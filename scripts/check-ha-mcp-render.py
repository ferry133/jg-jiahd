#!/usr/bin/env python3
"""ha_im_token renders HA_MCP_URL and Secret ha-im-token, derived from the ha_app tenant; nothing else moves.

jgct#237 (fleet-ops im-home-automation 3.1/3.2; jg-base#221/#232). On real
makejinja renders of the fixtures check-tenant-render.py maintains:

1. **No HA, no change**: no fixture renders HA_MCP_URL or a ha-im-token file.
   With `--against <ref>` each is byte-identical to the template at <ref>
   (not in CI, for check-tenant-render.py's reason).
2. **ha_app without a token changes nothing**: the HA tenant's render equals
   the same tenant without `ha_app`, file for file -- the first render, before
   HA has minted a token, must be the quiet one.
3. **ha_app with a token**: cluster-secrets HA_MCP_URL is
   `https://<ha_app>.<tenant>.<domain>/api/mcp`; tenants/kustomization lists
   ha-im-token.sops.yaml; Secret ha-im-token is in `claudecode` with exactly
   `token`, carrying the fixture's value; the token is not in cluster-secrets;
   and nothing outside cluster-secrets, the tenants kustomization and the new
   file differs from the token-less render.
4. **Refusals**, each with its own token and no credential in the message:
   a token without an ha_app tenant, a token with only the HA extra, a token
   on two lines. cue vet refuses a bad label and two ha_app tenants, and
   accepts the good scenario.

Exit 0 pass, 1 fail, 2 could not measure. A failure wins.
"""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("tr", ROOT / "scripts" / "check-tenant-render.py")
tr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tr)

CS = tr.CS
SECRET = "kubernetes/tenants/ha-im-token.sops.yaml"
TKZ = "kubernetes/tenants/kustomization.yaml"
TOKEN = "placeholder-ha-im-token"
HA = dict(name="homeauto", repository="fixture/home-automation", kind="vendor")
WANT_URL = "https://ha.homeauto.{domain}/api/mcp"


def cs_data(files: dict[str, bytes]) -> dict:
    for d in tr.docs(files[CS]):
        if tr.ident(d) == ("Secret", "cluster-secrets"):
            return d.get("stringData") or {}
    return {}


def scenario(base: dict, ha_app: bool, token: bool, **extra) -> dict:
    repo = dict(HA, ha_app="ha") if ha_app else dict(HA)
    f = dict(base, app_repos=[repo], **extra)
    if token:
        f["ha_im_token"] = TOKEN
    return f


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--tree", type=Path, default=ROOT)
    ap.add_argument("--against", metavar="REF")
    args = ap.parse_args()
    failures: list[str] = []
    base = next((f for n, f, _ in tr.FIXTURES if n == tr.TENANT_BASE), None)
    refusals = 0
    try:
        if base is None:
            raise tr.CannotMeasure(f"fixture {tr.TENANT_BASE!r} is gone from check-tenant-render.py")
        with tempfile.TemporaryDirectory(prefix="ha-mcp-render.") as tmp:
            key = Path(tmp) / "age.key"
            subprocess.run([tr.tool("age-keygen"), "-o", str(key)], capture_output=True, check=True)
            ref_tree = None
            if args.against:
                ref_tree = Path(tmp) / "ref"
                ref_tree.mkdir()
                tr.checkout(args.against, ref_tree)

            def render(f):
                return tr.render(args.tree, f, [], key)

            # 1. no HA (the four fixtures, and a vendor tenant without ha_app)
            population = [(n, f, nodes) for n, f, nodes in tr.FIXTURES]
            population.append(("tenant-no-ha", scenario(base, False, False), []))
            for name, fixture, nodes in population:
                try:
                    files = tr.render(args.tree, fixture, nodes, key)
                    before = tr.render(ref_tree, fixture, nodes, key) if ref_tree else None
                except RuntimeError as e:
                    failures.append(f"[{name}] render failed: {e}")
                    continue
                bad = []
                if "HA_MCP_URL" in cs_data(files):
                    bad.append(f"[{name}] no HA, yet cluster-secrets has HA_MCP_URL")
                if SECRET in files:
                    bad.append(f"[{name}] no HA, yet {SECRET} rendered")
                if before is not None:
                    bad += [f"[{name}] differs from {args.against}: {d}"
                            for d in tr.diff_names(before, files)]
                failures += bad
                if not bad:
                    print(f"ok  [{name}] no HA_MCP_URL, no ha-im-token"
                          + (f"; byte-identical to {args.against}" if before is not None else ""))

            # 2. ha_app alone is quiet
            plain = render(scenario(base, False, False))
            quiet = render(scenario(base, True, False))
            diff = tr.diff_names(plain, quiet)
            if diff:
                failures.append(f"[ha-app-no-token] ha_app without a token changed the render: {diff}")
            else:
                print("ok  [ha-app-no-token] ha_app without a token renders exactly what the tenant renders without it")

            # 3. ha_app + token
            files = render(scenario(base, True, True))
            bad = []
            url = cs_data(files).get("HA_MCP_URL")
            want = WANT_URL.format(domain=base["cloudflare_domain"])
            if url != want:
                bad.append(f"[ha] HA_MCP_URL {url!r}, expected {want!r}")
            listed = next((d.get("resources") or [] for d in tr.docs(files.get(TKZ, b""))), [])
            if "ha-im-token.sops.yaml" not in listed:
                bad.append(f"[ha] {TKZ} does not list ha-im-token.sops.yaml -- the Secret would never be applied")
            sec = {tr.ident(d): d for d in tr.docs(files.get(SECRET, b""))}.get(("Secret", "ha-im-token"))
            if sec is None:
                bad.append(f"[ha] Secret ha-im-token not rendered in {SECRET}")
            else:
                if sec.get("metadata", {}).get("namespace") != "claudecode":
                    bad.append("[ha] Secret ha-im-token not in claudecode")
                sd = sec.get("stringData") or {}
                if sorted(sd) != ["token"]:
                    bad.append(f"[ha] Secret ha-im-token keys {sorted(sd)}, expected ['token']")
                elif sd["token"] != TOKEN:
                    bad.append("[ha] Secret ha-im-token does not carry the fixture's token")
            if TOKEN.encode() in files[CS]:
                bad.append("[ha] the token is in cluster-secrets")
            allowed = {f"differs: {CS}", f"differs: {TKZ}", f"only in second: {SECRET}"}
            stray = [d for d in tr.diff_names(quiet, files) if d not in allowed]
            if stray:
                bad.append(f"[ha] the token changed more than its three files: {stray}")
            failures += bad
            if not bad:
                print(f"ok  [ha] HA_MCP_URL={want}; ha-im-token in claudecode, listed, carrying the token; "
                      "nothing else moved")

            # 4. refusals
            for name, fixture, token in (
                ("token-no-ha-app", scenario(base, False, True), "no app_repos entry declares ha_app"),
                ("token-extra-only", dict(base, ha_im_token=TOKEN,
                                          extras=list(base.get("extras") or []) + ["default/home-assistant"]),
                 "extra gets none"),
                ("token-two-lines", dict(scenario(base, True, False), ha_im_token=TOKEN + "\nx"),
                 "spans more than one line"),
            ):
                try:
                    render(fixture)
                except RuntimeError as e:
                    msg = str(e)
                    if token not in msg:
                        failures.append(f"[{name}] refused, but not for its own reason "
                                        f"(no {token!r}): {msg[-200:]}")
                    elif TOKEN in msg:
                        failures.append(f"[{name}] refused, and the message carries the token")
                    else:
                        refusals += 1
                        print(f"ok  [{name}] refused: {token!r}")
                    continue
                failures.append(f"[{name}] rendered; it must be refused ({token!r})")
            two = dict(base, app_repos=[dict(HA, ha_app="ha"),
                                        dict(name="other", repository="fixture/other",
                                             kind="vendor", ha_app="ha")])
            for name, fixture, accept in (
                ("vet-ha", scenario(base, True, True), True),
                ("vet-bad-label", dict(base, app_repos=[dict(HA, ha_app="Ha.x")]), False),
                ("vet-two-ha-apps", two, False),
            ):
                problem = tr.vet(args.tree, fixture, [])
                if (problem is None) != accept:
                    failures.append(f"[{name}] cue vet {'refused' if problem else 'accepted'} it"
                                    + (f": {problem}" if problem else ""))
                else:
                    print(f"ok  [{name}] cue vet {'accepts' if accept else 'refuses'}")
    except tr.CannotMeasure as e:
        if failures:
            print("\n".join("FAIL " + f for f in failures))
            return 1
        print(f"COULD NOT MEASURE: {e}")
        return 2
    except RuntimeError as e:
        failures.append(f"a good scenario failed to render (guard or template defect): {e}")
    if failures:
        print("\n".join("FAIL " + f for f in failures))
        return 1
    print(f"PASS -- {len(tr.FIXTURES) + 1} renders without HA unchanged"
          + (f" (byte-identical to {args.against})" if args.against else "")
          + f"; ha_app alone quiet; ha_app + token renders URL and Secret only; "
          f"{refusals} refusals each for its own reason; 3 cue vet verdicts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
