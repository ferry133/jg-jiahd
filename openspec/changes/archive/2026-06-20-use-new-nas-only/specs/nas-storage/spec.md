## ADDED Requirements

### Requirement: Single NAS backend

The cluster SHALL use exactly one NAS appliance, `10.9.2.13`, as the NFS backend for all persistent storage. No configuration in `jg-jiahd` or `jg-base` SHALL reference the old NAS `10.9.1.12`.

#### Scenario: No old-NAS references remain

- **WHEN** the `jg-jiahd` and `jg-base` repositories are searched for `10.9.1.12`
- **THEN** no manifest, template, rendered file, or secret references it

#### Scenario: Single source of truth for NAS address

- **WHEN** the NAS server address is needed by a templated resource
- **THEN** it is derived from the single `nas_server` value (`10.9.2.13`) in `cluster.yaml` (surfaced as `NAS_SERVER`), not hard-coded

### Requirement: Dynamic storage class targets the new NAS

The `sc-nas` StorageClass SHALL provision NFS volumes from `10.9.2.13`. Because StorageClass parameters are immutable, the StorageClass SHALL be recreated to apply the new server.

#### Scenario: New PVC provisions on the new NAS

- **WHEN** a new PVC requests `sc-nas` after the change
- **THEN** its bound PersistentVolume has `spec.nfs.server == 10.9.2.13`

#### Scenario: nfs-subdir HelmRelease is healthy

- **WHEN** Flux reconciles `storage/nfs-subdir` after the StorageClass is recreated
- **THEN** the HelmRelease becomes `Ready=True` (no immutable-field upgrade failure)

### Requirement: Static NFS PVs target the new NAS

The static (hand-authored) NFS PersistentVolumes — `linebot-knowledge-nas`, `linebot-jia-homedesign-nas`, and `postgres-backup-nas` — SHALL point at `10.9.2.13`. Because `spec.nfs.server` is immutable, each PV (and its bound PVC) SHALL be recreated.

#### Scenario: Static PV bound to the new NAS

- **WHEN** the static PVs are reconciled after the change
- **THEN** each is `Bound` with `spec.nfs.server == 10.9.2.13` and its consuming pod mounts successfully

### Requirement: Data continuity across the migration

The data backing each NFS volume SHALL be present on `10.9.2.13` before the workload is cut over, so no application loses data. Stateful workloads (at least Postgres and MQTT) SHALL be quiesced during their copy → repoint → restart cutover.

#### Scenario: Workload data intact after cutover

- **WHEN** a workload (e.g. Postgres) is restarted against its new-NAS volume
- **THEN** it reads the same data it had on the old NAS (row counts / files match a pre-cutover snapshot)

#### Scenario: No partial-write corruption for stateful apps

- **WHEN** a stateful workload's underlying data is copied to the new NAS
- **THEN** the workload is stopped (or its PVC detached) for the duration of the copy and the cutover

### Requirement: NAS health monitoring follows the new NAS

The `daily-check` monitoring job SHALL probe `10.9.2.13` for NAS reachability.

#### Scenario: Daily check reports the new NAS

- **WHEN** the `daily-check` job runs after the change
- **THEN** its NAS reachability line names `10.9.2.13` and reports it reachable
