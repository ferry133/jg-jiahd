## 1. Prep (paths confirmed: old `/volume2/<x>` → new `/volume3/<x>`)

- [x] 1.1 Confirm Synology Drive ShareSync shows all four shares mirrored to `/volume3/{claudecode,jia.homedesign,knowledge,backup1}` on `10.9.2.13` and status is "up to date". (claudecode/jia.homedesign/knowledge = two-way, Up to date. NOTE: old `backup1` syncs to a new-NAS folder named `backup2`, **Download only** — see 7.4 decision.)
- [x] 1.2 From the cluster, verify NFS reachability of `10.9.2.13:2049` (a temporary test pod mounting `10.9.2.13:/volume3/...`, or reuse the synophoto showcase-vault mount as proof). (All four /volume3 shares mount RO; `jia.homedesign` needed an NFS-permission fix on the NAS, now done.)

## 2. Verify mirror (ShareSync already copies — do not rsync)

- [x] 2.1 Spot-check file counts on `/volume3/claudecode` (incl. all `jgu5-*` / `jg-jiahd-*` subdirs), `/volume3/jia.homedesign`, `/volume3/knowledge`, `/volume3/backup1` vs the old `/volume2/*` equivalents. (claudecode: old 6216 / new 6204 files, ~147 MB both — delta is live DB writes; jia/knowledge rely on ShareSync "Up to date".)
- [x] 2.2 Record baseline checks: per-share file counts, and a Postgres row-count / `pg_dump` snapshot taken from the running DB. (Baseline rows: episodes 107, knowledge 21, line_user_projects 23, line_users 20, projects 7, sites 3, trello_boards 20, working_memory 4.)

## 3. Protect old data

- [x] 3.1 Patch every old PV bound to `10.9.1.12` to `persistentVolumeReclaimPolicy: Retain` (so later PV/PVC deletion never reclaims old-NAS data). DONE — 9 PVs set to Retain.

> **Method A (subdir prefix fix).** `sc-nas` dynamic dirs are named `jg-jiahd-<ns>-<pvc>`, but most data still lives under the old `jgu5-<ns>-<pvc>` subdir on `/volume3/claudecode`. For each prefix-mismatched dynamic volume, after quiescing the workload and letting ShareSync settle, copy on the new NAS `cp -a /volume3/claudecode/jgu5-<x> /volume3/claudecode/jg-jiahd-<x>` (keep the `jgu5-` original as backup), then recreate the PVC so the provisioner reuses the populated `jg-jiahd-<x>` dir. Affected: db/postgres-data, claudecode/cc-claude-config, claudecode/cc-claude-workspace, mqtt/mosquitto-data, claudecode/claude-code. `linebot/synophoto-sessions` already uses the `jg-jiahd-` prefix (no copy). The 3 static PVs are whole-share (no subdir, no copy).

## 4. Config changes (repos)

- [x] 4.1 `jg-jiahd` `cluster.yaml`: set `nas_server: "10.9.2.13"`, `nas_path: "/volume3/claudecode"`, `nas_coding_path: "/volume3/coding"` (server + `/volume2`→`/volume3`).
- [x] 4.2 `jg-jiahd`: `task configure --yes` → re-render + re-encrypt `cluster-secrets`; review diff is limited to NAS-derived fields; commit + push.
- [x] 4.3 `jg-base`: repoint static PVs — `linebot/app/knowledge-pvc.yaml` (`10.9.1.12:/volume2/knowledge` → `10.9.2.13:/volume3/knowledge`), `linebot/app/jia-homedesign-pvc.yaml` (`…/volume2/jia.homedesign` → `…/volume3/jia.homedesign`), `postgres/app/backup.yaml` (`…/volume2/backup1` → `…/volume3/backup1`); commit + push.

## 5. Cutover — stateless / config volumes

- [x] 5.1 Scale down `claude-code` instances; recreate their `sc-nas` PVCs (and the recreated `sc-nas` StorageClass, see 6.1) on the new NAS; scale up; verify config/workspace present.
- [x] 5.2 Recreate linebot `knowledge` + `jia.homedesign` static PV/PVC on the new NAS; restart linebot pods; verify knowledge files and homedesign data mount.

## 6. Cutover — dynamic StorageClass

- [x] 6.1 `kubectl delete sc sc-nas`; reconcile/`suspend`+`resume` the `storage/nfs-subdir` HelmRelease so Helm recreates `sc-nas` with `server=10.9.2.13`; confirm HR `Ready=True`.

## 7. Cutover — stateful (Postgres, MQTT)

- [x] 7.1 `flux suspend` / scale Postgres + MQTT to 0 (quiesce writers).
- [x] 7.2 Let ShareSync settle (confirm "up to date" so the latest writes reached `/volume3`); recreate their PVCs/PVs on the new NAS (map old subdir prefix → recreated PVC subdir).
- [x] 7.3 Scale Postgres + MQTT back up; verify Postgres row counts match the 2.2 snapshot and MQTT reconnects.
- [x] 7.4 Recreate the `postgres-backup` PV/PVC on the new NAS; run a manual backup job and confirm it writes to `10.9.2.13:/volume3/backup1`.

## 8. Verify

- [x] 8.1 All NFS PVCs `Bound` with `spec.nfs.server == 10.9.2.13`; all consuming pods Running.
- [x] 8.2 All Flux Kustomizations + HelmReleases `Ready`.
- [x] 8.3 Trigger `daily-check`; confirm the NAS line names `10.9.2.13` and reports reachable.
- [x] 8.4 Grep both repos: zero `10.9.1.12` references remain.

## 9. Cleanup

- [x] 9.1 Delete orphaned `Retain`ed old PVs once verification passes.
- [x] 9.2 Update memory `project_cluster.md` (NAS is now `10.9.2.13`); note the old NAS is no longer referenced.
