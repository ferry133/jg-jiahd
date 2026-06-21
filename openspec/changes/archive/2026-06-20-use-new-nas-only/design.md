## Context

NFS storage is currently split between two Synology NAS appliances:

- **Old NAS `10.9.1.12`** — backs almost everything: `sc-nas` dynamic StorageClass (`/volume2/claudecode/<prefix>-<ns>-<pvc>`), and three static PVs (`/volume2/jia.homedesign`, `/volume2/knowledge`, `/volume2/backup1`).
- **New NAS `10.9.2.13`** — already serves only synophoto's `showcase-vault` (`/volume3/showcase-vault`), proving the new NAS is reachable from the cluster network.

Resolved inputs (from owner):
- **Paths**: folder names are identical on both NAS; only the volume differs — old `/volume2/<x>` maps to new `/volume3/<x>`. So every path also changes `/volume2` → `/volume3`.
- **Data copy**: Synology Drive **2-way ShareSync** is already configured between the two NAS, so each `/volume2/<x>` is continuously mirrored to `/volume3/<x>`. No manual bulk rsync is needed — the migration only needs to *verify* the mirror and let it settle before stateful cutover.
- **Downtime**: a cutover window is acceptable.

`nas_server` in `cluster.yaml` is the single templated source for the old IP (→ `NAS_SERVER` → `sc-nas`, `claude-code`, `daily-check`). The three static PVs and `postgres-backup` hard-code `10.9.1.12` directly in `jg-base`.

Hard constraints discovered during recon:
- A StorageClass's `parameters` (incl. `server`) are **immutable** — Helm upgrade fails with "field is immutable" (same failure mode already hit on the `pathPattern` rename). The StorageClass must be deleted and recreated.
- A bound PV's `spec.nfs.server` is **immutable** — static PVs and existing dynamic PVs must be recreated to move servers.
- Existing dynamic PV subdirectories carry mixed prefixes (`jgu5-…` and `jg-jiahd-…`) under `/volume2/claudecode`.

## Goals / Non-Goals

**Goals:**
- All cluster NFS storage served from `10.9.2.13`; zero references to `10.9.1.12` in either repo.
- No application data loss; stateful workloads cut over cleanly.
- Keep the single-source-of-truth pattern (`nas_server` in `cluster.yaml`) intact.

**Non-Goals:**
- Physically decommissioning / powering off the old NAS hardware.
- Changing the NAS *paths* / share layout beyond what the server move requires.
- Migrating synophoto showcase-vault (already on the new NAS).

## Decisions

**D1 — Flip the single `nas_server` var; manually edit only the hard-coded PVs.**
Change `cluster.yaml` `nas_server: 10.9.1.12 → 10.9.2.13`, then `task configure` re-renders `sc-nas`, `claude-code`, and `daily-check`/`cluster-secrets`. Separately edit the three hard-coded `jg-base` static PV manifests. *Alternative considered:* parameterize the static PVs through `NAS_SERVER` too — better long-term but a larger refactor; deferred to keep this change focused (noted as follow-up).

**D2 — Rely on the existing Synology Drive 2-way ShareSync; verify, don't re-copy.**
ShareSync already mirrors `/volume2/<x>` (old) ↔ `/volume3/<x>` (new) continuously, so the data is already present on the new NAS. The migration's data step is to *verify* the mirror is complete and *let it settle* (briefly pause writers) before each stateful cutover, rather than running a manual bulk rsync. *Alternative considered:* a one-off in-cluster rsync Job — unnecessary given ShareSync, kept only as a fallback if the mirror is found incomplete. *Caveat:* 2-way sync means writes on either side propagate both ways; after cutover only the new NAS is written (old has no active writer), so the mirror simply trickles new→old and no conflict arises.

**D3 — Recreate immutable resources; preserve old data with `Retain`.**
Before deleting any old PV, patch its `persistentVolumeReclaimPolicy` to `Retain` so deleting the PV/PVC never triggers NFS data reclaim on the old NAS. Then delete + recreate the `sc-nas` StorageClass and each PVC/PV so they bind to `10.9.2.13`. The old NAS stays intact as the rollback copy until verification passes.

**D4 — Per-workload cutover ordering (stop → final-sync → repoint → start → verify).**
- Stateless / config-only (claude-code, linebot knowledge & jia.homedesign): scale down, recreate PVC/PV, scale up.
- Postgres (and MQTT): `flux suspend` the HelmRelease / scale Deployment to 0 → final delta `rsync` (hot data must be quiesced) → recreate PVC/PV on new NAS → scale up → verify row counts vs a pre-cutover `pg_dump`/count snapshot.

**D5 — Use the established Flux recovery playbook.**
StorageClass/HelmRelease recreation reuses the known pattern: `kubectl delete sc sc-nas`, then `suspend`+`resume` the `nfs-subdir` HelmRelease. Prefer `kubectl patch`/`annotate` over the `flux` CLI (the CLI hangs in this environment).

## Risks / Trade-offs

- **Data loss / incomplete copy** → keep old NAS fully intact (`Retain` + no deletion of old data); verify every volume (file counts, and Postgres row counts) before declaring done; old NAS is the rollback source.
- **Hot-copy corruption of Postgres** → stop Postgres before the final sync; never copy a live PGDATA.
- **Path change `/volume2` → `/volume3`** (resolved): every NAS path moves volumes, so `nas_path`, `nas_coding_path`, and the three static-PV paths must all be updated alongside the server — missing one would mount the wrong (or empty) directory.
- **ShareSync conflict / lag** → before each stateful cutover, quiesce the writer and confirm ShareSync shows "up to date" so the new NAS has the latest writes; do not cut over mid-sync.
- **Downtime** → linebot, Postgres, MQTT, claude-code are briefly unavailable during cutover; schedule a low-traffic window.
- **Dynamic PV prefix mix** (`jgu5-…`, `jg-jiahd-…`) → copy whole `/volume2/claudecode` so all prefixed subdirs come across; recreated PVCs get fresh `jg-jiahd-…` dirs, so map old→new subdir names during the final sync for each stateful PVC.

## Migration Plan

1. **Prep**: confirm ShareSync has mirrored all shares to `/volume3/{claudecode,jia.homedesign,knowledge,backup1}` on `10.9.2.13` and is "up to date".
2. **Verify mirror** (no manual copy): spot-check file counts on `/volume3/*` vs `/volume2/*`; rely on ShareSync rather than rsync.
3. **Snapshot** baselines (Postgres row counts, file counts per share).
4. **Quiesce + final sync + cutover** per workload (D4), patching old PVs to `Retain` first (D3).
5. **Config flip**: `cluster.yaml` `nas_server`; `task configure`; edit 3 static PVs in `jg-base`; commit + push both repos; Flux reconcile; recreate `sc-nas`.
6. **Verify**: all PVCs `Bound` on `10.9.2.13`; apps healthy; data checks pass; `daily-check` names `10.9.2.13`.
7. **Cleanup**: confirm zero `10.9.1.12` references; remove orphaned old PVs.

**Rollback**: revert the two commits (restore `nas_server` and PV manifests to `10.9.1.12`), recreate StorageClass/PVs; old NAS data untouched (`Retain`), so workloads return to their original volumes.

## Open Questions

Resolved with the owner:
- **Paths** — new NAS uses `/volume3/<x>` for the same folder names as old `/volume2/<x>`; all paths change volumes accordingly.
- **Data copy** — Synology Drive 2-way ShareSync already mirrors the data; this change verifies rather than copies.
- **Downtime** — a cutover window is acceptable.

Still open:
- Should the three hard-coded static PVs be parameterized via `NAS_SERVER`/`NAS_PATH` now (D1 alternative) or left as a follow-up? (Default: leave as a follow-up to keep this change focused.)
