## 1. Prep (paths confirmed: old `/volume2/<x>` → new `/volume3/<x>`)

- [ ] 1.1 Confirm Synology Drive ShareSync shows all four shares mirrored to `/volume3/{claudecode,jia.homedesign,knowledge,backup1}` on `10.9.2.13` and status is "up to date".
- [ ] 1.2 From the cluster, verify NFS reachability of `10.9.2.13:2049` (a temporary test pod mounting `10.9.2.13:/volume3/...`, or reuse the synophoto showcase-vault mount as proof).

## 2. Verify mirror (ShareSync already copies — do not rsync)

- [ ] 2.1 Spot-check file counts on `/volume3/claudecode` (incl. all `jgu5-*` / `jg-jiahd-*` subdirs), `/volume3/jia.homedesign`, `/volume3/knowledge`, `/volume3/backup1` vs the old `/volume2/*` equivalents.
- [ ] 2.2 Record baseline checks: per-share file counts, and a Postgres row-count / `pg_dump` snapshot taken from the running DB.

## 3. Protect old data

- [ ] 3.1 Patch every old PV bound to `10.9.1.12` to `persistentVolumeReclaimPolicy: Retain` (so later PV/PVC deletion never reclaims old-NAS data).

## 4. Config changes (repos)

- [ ] 4.1 `jg-jiahd` `cluster.yaml`: set `nas_server: "10.9.2.13"`, `nas_path: "/volume3/claudecode"`, `nas_coding_path: "/volume3/coding"` (server + `/volume2`→`/volume3`).
- [ ] 4.2 `jg-jiahd`: `task configure --yes` → re-render + re-encrypt `cluster-secrets`; review diff is limited to NAS-derived fields; commit + push.
- [ ] 4.3 `jg-base`: repoint static PVs — `linebot/app/knowledge-pvc.yaml` (`10.9.1.12:/volume2/knowledge` → `10.9.2.13:/volume3/knowledge`), `linebot/app/jia-homedesign-pvc.yaml` (`…/volume2/jia.homedesign` → `…/volume3/jia.homedesign`), `postgres/app/backup.yaml` (`…/volume2/backup1` → `…/volume3/backup1`); commit + push.

## 5. Cutover — stateless / config volumes

- [ ] 5.1 Scale down `claude-code` instances; recreate their `sc-nas` PVCs (and the recreated `sc-nas` StorageClass, see 6.1) on the new NAS; scale up; verify config/workspace present.
- [ ] 5.2 Recreate linebot `knowledge` + `jia.homedesign` static PV/PVC on the new NAS; restart linebot pods; verify knowledge files and homedesign data mount.

## 6. Cutover — dynamic StorageClass

- [ ] 6.1 `kubectl delete sc sc-nas`; reconcile/`suspend`+`resume` the `storage/nfs-subdir` HelmRelease so Helm recreates `sc-nas` with `server=10.9.2.13`; confirm HR `Ready=True`.

## 7. Cutover — stateful (Postgres, MQTT)

- [ ] 7.1 `flux suspend` / scale Postgres + MQTT to 0 (quiesce writers).
- [ ] 7.2 Let ShareSync settle (confirm "up to date" so the latest writes reached `/volume3`); recreate their PVCs/PVs on the new NAS (map old subdir prefix → recreated PVC subdir).
- [ ] 7.3 Scale Postgres + MQTT back up; verify Postgres row counts match the 2.2 snapshot and MQTT reconnects.
- [ ] 7.4 Recreate the `postgres-backup` PV/PVC on the new NAS; run a manual backup job and confirm it writes to `10.9.2.13:/volume3/backup1`.

## 8. Verify

- [ ] 8.1 All NFS PVCs `Bound` with `spec.nfs.server == 10.9.2.13`; all consuming pods Running.
- [ ] 8.2 All Flux Kustomizations + HelmReleases `Ready`.
- [ ] 8.3 Trigger `daily-check`; confirm the NAS line names `10.9.2.13` and reports reachable.
- [ ] 8.4 Grep both repos: zero `10.9.1.12` references remain.

## 9. Cleanup

- [ ] 9.1 Delete orphaned `Retain`ed old PVs once verification passes.
- [ ] 9.2 Update memory `project_cluster.md` (NAS is now `10.9.2.13`); note the old NAS is no longer referenced.
