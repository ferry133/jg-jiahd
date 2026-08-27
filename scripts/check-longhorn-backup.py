#!/usr/bin/env python3
"""Assert this cluster's Longhorn backup gate agrees with its Longhorn.

jg-base ships `Kustomization/longhorn-backup` SUSPENDED. It carries a
RecurringJob that writes to `LONGHORN_BACKUP_TARGET`, and this repo un-suspends
it with a patch wherever `longhorn_backup_target` is set.

Three facts have to agree and they come from three different places: the target
(cluster.yaml), the un-suspend patch (flux/cluster/ks.yaml), and whether
Longhorn is installed at all (`deploy_longhorn`, from `replicated_storage` or
`storage_backend`). Nothing forces them to.

`cue vet` cannot close this. It catches the outright contradiction
(`longhorn_backup_target` set together with `replicated_storage: false` --
measured, it reports "conflicting values true and false"), but not the case
that actually happens: `replicated_storage` simply absent. CUE sees an optional
field it may define as `true`, which is not an error, and plugin.py never reads
CUE's unified value anyway -- it reads cluster.yaml. Measured: target set,
`storage_backend: nfs`, `replicated_storage` absent renders
`deploy_longhorn=False` with `longhorn_backup=nfs`, and `cue vet` exits clean.

What that costs if unchecked: the per-user repo suspends `Kustomization/longhorn`,
jg-base's `longhorn-backup` selects ./nfs, and the RecurringJob is applied
against a CRD that no chart ever installed. The Kustomization goes Ready=False
and stays there, and the operator believes there is a nightly backup.

Runs against the RENDERED artifacts, after render-configs, for the same reason
check-backup-recipient.py does: the input someone meant to write and the output
that ships are different things, and only one of them reaches a cluster.

Exit 0 pass, 1 fail, 2 could not measure -- three outcomes, because a check
that cannot see its subject must not read as one that passed.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SECRET = Path('kubernetes/components/sops/cluster-secrets.sops.yaml')
CLUSTER_KS = Path('kubernetes/flux/cluster/ks.yaml')

# Schemes longhorn-manager knows how to write to. A typo here does not fail at
# render or at apply -- the BackupTarget CR simply reports available: false,
# which looks the same as a NAS that is merely unreachable.
SCHEMES = ('nfs://', 'cifs://', 's3://', 'azblob://', 'gcs://')

# Values a YAML 1.1 parser reads as something other than a string. The selector
# lands in stringData, and kustomize does not keep the quotes around the
# placeholder it is substituted into (ferry133/jg-base#16).
NOT_A_STRING = {
    '', '~', 'null', 'Null', 'NULL',
    'true', 'True', 'TRUE', 'false', 'False', 'FALSE',
    'yes', 'Yes', 'YES', 'no', 'No', 'NO',
    'on', 'On', 'ON', 'off', 'Off', 'OFF',
}


def value_of(text: str, key: str) -> str | None:
    m = re.search(rf'^\s+{re.escape(key)}:\s*(.*?)\s*$', text, re.M)
    if m is None:
        return None
    return m.group(1).strip().strip('"').strip("'")


def patched_suspend(ks_text: str, name: str) -> bool | None:
    """What the per-user ks.yaml patches `suspend` to for Kustomization `name`.

    True / False as patched, None if no patch targets it. Matching is per
    `- patch: |-` block and anchored on the whole name, so `longhorn` and
    `longhorn-backup` are never confused for each other -- a distinction this
    check depends on entirely.
    """
    result = None
    for block in ks_text.split('- patch: |-')[1:]:
        head = block.split('- patch: |-')[0]
        if not re.search(rf'^\s+name:\s*{re.escape(name)}\s*$', head, re.M):
            continue
        m = re.search(r'^\s+suspend:\s*(true|false)\s*$', head, re.M)
        if m:
            result = m.group(1) == 'true'
    return result


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    secret, cluster_ks = root / SECRET, root / CLUSTER_KS

    missing = [p for p in (secret, cluster_ks) if not p.is_file()]
    if missing:
        for p in missing:
            print(f'COULD NOT MEASURE  {p} does not exist')
        print('\nRun this after `render-configs`. Reporting "could not measure"')
        print('rather than passing: an absent artifact is not a correct one.')
        return 2

    secret_text = secret.read_text()
    target = value_of(secret_text, 'LONGHORN_BACKUP_TARGET')

    if target is None:
        print('COULD NOT MEASURE  LONGHORN_BACKUP_TARGET is not in the rendered')
        print('  secret. This repo\'s templates/ predate ferry133/jg-base#7. A')
        print('  per-user repo carries its own copy of templates/, and')
        print('  `task configure` exits 0 either way, so this is exactly the')
        print('  state that reads like a pass. Sync templates/ first.')
        return 2

    ks_text = cluster_ks.read_text()
    backup_patch = patched_suspend(ks_text, 'longhorn-backup')
    longhorn_patch = patched_suspend(ks_text, 'longhorn')

    has_target = bool(target)
    # jg-base ships longhorn-backup suspended, so no patch means off.
    backup_on = backup_patch is False
    # longhorn itself ships active, so no patch means on.
    longhorn_on = longhorn_patch is not True

    failed = []

    if has_target and not backup_on:
        failed.append(
            f'a backup target is set ({target}) but nothing un-suspends '
            'Kustomization/longhorn-backup, so the RecurringJob is never '
            'applied: Longhorn would have a target and never write to it')
    if not has_target and backup_on:
        failed.append(
            'Kustomization/longhorn-backup is un-suspended with no '
            'LONGHORN_BACKUP_TARGET, so the RecurringJob runs and fails '
            'nightly against an unset target')
    if has_target and not target.startswith(SCHEMES):
        failed.append(
            f'LONGHORN_BACKUP_TARGET {target!r} has no scheme Longhorn '
            f'accepts ({", ".join(SCHEMES)}); the BackupTarget CR reports '
            'available: false, which looks the same as an unreachable NAS')
    if backup_on and not longhorn_on:
        failed.append(
            'longhorn-backup is un-suspended but this cluster suspends '
            'Kustomization/longhorn, so the RecurringJob is applied against a '
            'CRD no chart installs. Set replicated_storage: true (or '
            'storage_backend: "replicated") if Longhorn is wanted here, or '
            'drop longhorn_backup_target if it is not')

    print(f'LONGHORN_BACKUP_TARGET = {target!r}')
    print(f'longhorn-backup        = {"un-suspended" if backup_on else "suspended"}'
          f'  (patch: {backup_patch})')
    print(f'longhorn               = {"active" if longhorn_on else "suspended"}'
          f'  (patch: {longhorn_patch})')
    print()

    if failed:
        for f in failed:
            print(f'FAIL  {f}')
        return 1

    if not has_target:
        print('ok - no Longhorn backup configured; longhorn-backup stays')
        print('     suspended as jg-base ships it, and the chart render is')
        print('     byte-identical to a cluster that never had this variable')
        print('     (measured with helm template).')
    else:
        print('ok - target set, longhorn-backup un-suspended, Longhorn installed.')
        print()
        print('     NOT checked here, and not checkable from a template repo:')
        print('     whether the export accepts writes from longhorn')
        print('     instance-manager, and whether a backup has ever been')
        print('     restored. A backup target that has never restored is a')
        print('     hypothesis.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
