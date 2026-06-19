## Why

The cluster's NFS storage is split across two NAS appliances: most workloads use the old NAS at `10.9.1.12` (`nas_server` in `cluster.yaml`, plus three hard-coded static PVs), while only synophoto's showcase-vault already lives on the new NAS at `10.9.2.13`. We want to retire the old NAS and serve **all** cluster storage from the new NAS `10.9.2.13` only, so there is a single storage backend to maintain and back up.

## What Changes

- Point the cluster's single NAS variable `nas_server` (`cluster.yaml`) from `10.9.1.12` to `10.9.2.13`. This re-renders everything templated from `${NAS_SERVER}`: the `sc-nas` StorageClass (`storage/nfs-subdir`), the `claude-code` NAS mount, and the `daily-check` reachability probe.
- Repoint the three **hard-coded** static PVs in `jg-base` from `10.9.1.12` to `10.9.2.13`: `linebot-knowledge-nas`, `linebot-jia-homedesign-nas`, `postgres-backup-nas`.
- **BREAKING**: the `sc-nas` StorageClass `server` parameter and every existing PV's `spec.nfs.server` are **immutable**. All NFS-backed PVs/PVCs (postgres data, claude-code config/workspace, mqtt, the three static PVs) must be recreated to bind to the new server, and their data copied from the old NAS to the new NAS first.
- Update every NAS **path** from `/volume2/<x>` to `/volume3/<x>` (same folder names, new volume): `nas_path`, `nas_coding_path`, and the three static-PV paths.
- Data is already mirrored by **Synology Drive 2-way ShareSync** (`/volume2/<x>` ↔ `/volume3/<x>`), so no manual bulk copy is needed — the migration verifies the mirror and quiesces writers briefly before stateful cutover (especially Postgres).
- After verification, decommission the old NAS reference entirely — no remaining `10.9.1.12` in either repo.

## Capabilities

### New Capabilities
- `nas-storage`: which NAS/NFS server backs the cluster's persistent storage (the `sc-nas` StorageClass, static NFS PVs, and the daily-check NAS probe), and the requirement that exactly one NAS (`10.9.2.13`) is used.

### Modified Capabilities
<!-- none — no existing specs in openspec/specs/ -->

## Impact

- **`jg-jiahd`**: `cluster.yaml` (`nas_server`), re-render via `task configure`, re-encrypted `cluster-secrets` (`NAS_SERVER`).
- **`jg-base`**: `storage/nfs-subdir` & `claudecode/claude-code` helmreleases (templated), and hard-coded static PVs — `linebot/app/knowledge-pvc.yaml`, `linebot/app/jia-homedesign-pvc.yaml`, `postgres/app/backup.yaml`.
- **Live cluster state**: delete + recreate the `sc-nas` StorageClass and all NFS PVCs/PVs; brief downtime for Postgres, MQTT, claude-code, and linebot during cutover.
- **Data**: served by ShareSync at `10.9.2.13:/volume3/*` (claudecode, jia.homedesign, knowledge, backup1); verify the mirror is up to date before cutover.
- **Out of scope**: physically decommissioning / powering down the old NAS hardware (only the cluster's references are removed).
