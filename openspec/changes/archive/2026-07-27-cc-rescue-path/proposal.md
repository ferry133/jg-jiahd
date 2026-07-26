# Proposal: cc-rescue-path

> Retroactive documentation — implemented and verified 2026-07-26, documented 2026-07-27.

## Why

jg-jiahd is moving to a remote network that cannot be reached directly. The only management path was kubectl via Omni (`kubeconfig-sa`), a single point of failure: if Omni or SideroLink is down, the cluster becomes unmanageable remotely. The cc.jiahd.cc web terminal (claudecode extra) already reached the cluster through an independent channel (Cloudflare Tunnel), but it could not act as a rescue path: no kubectl, no RBAC, a broken NAS mount (root-only NFS export vs uid-1000 pod), Claude login lost on every pod restart, and a fixed basic-auth credential as the only gate on a public URL.

## What Changes

- Add kubectl v1.36.0 to the `ghcr.io/ferry133/claude-code` image (k8scc).
- Bind the cc pod to a shared ServiceAccount `claude-code` with **cluster-admin** (user-confirmed): in-pod kubectl talks to `10.96.0.1` directly, no Omni dependency.
- Run the pod as root (`runAsUser: 0`): the NAS NFS exports only allow root, uid 1000 saw the coding mount as `d---------`. Retires the setcap/NET_RAW file-capability workaround (root's default caps cover it).
- Persist Claude login: `CLAUDE_CONFIG_DIR=/home/claude/.claude` puts onboarding/credentials on the claude-config PVC; keyring dir mounted from the same PVC.
- **BREAKING (auth):** replace ttyd basic auth with Auth0 OIDC via an oauth2-proxy v7.15.3 sidecar (reuses the synophoto Auth0 app; allowlist `jiahdadm@gmail.com` only). ttyd binds `127.0.0.1` and requires the proxy's `X-Forwarded-Email` header — `:7681` is unreachable from the LAN; the old basic-auth credential grants nothing.
- Template all of the above conditionally in jg-cluster-template (`claudecode_auth0_domain` switches modes), so client clusters keep ttyd basic auth until they opt in.

## Capabilities

### New Capabilities
- `remote-terminal`: browser-accessible in-cluster Claude Code terminal (cc.<domain>) as a management/rescue path independent of Omni — authentication, cluster access, LAN access, state persistence.

### Modified Capabilities
<!-- none — nas-storage requirements unchanged; the root-mount rule was already NAS policy -->

## Impact

- **k8scc** (`ghcr.io/ferry133/claude-code`): +kubectl, env-gated `TTYD_INTERFACE`/`TTYD_AUTH_HEADER`, `claude-session` reads `TTYD_USER`. Commits `86e7212`…`0b291a6`.
- **jg-base**: `claudecode/claude-code/app/rbac.yaml` (SA + cluster-admin CRB), secret keys `OAUTH2_PROXY_*`, `ALLOWED_EMAILS`. Commits `6dedb7f`, `9ef6e1d`.
- **jg-cluster-template**: instances helmrelease template (conditional OIDC mode), `cluster.schema.cue` +5 optional fields, cluster-secrets j2 +4 vars, `cluster.sample.yaml` docs. Commits `3c1731e`…`cdfbddc`.
- **jg-jiahd**: `cluster.yaml` values (gitignored), rendered manifests. Commits `390b029`…`313dafb`.
- **Auth0**: callback/logout/origin URLs for cc.jiahd.cc added to the existing app (dashboard, done by user).
