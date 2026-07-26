# Design: cc-rescue-path

## Context

Talos nodes reach Omni over SideroLink (outbound WireGuard) and the cluster publishes `*.jiahd.cc` through an in-cluster `cloudflared` → Cloudflare Tunnel (also outbound). Behind a remote NAT both channels keep working, but they share nothing: Omni carries kubectl/talosctl, the tunnel carries HTTP. The claudecode extra (`cc` pod, ttyd + Claude Code CLI, hostNetwork) already sat behind the tunnel — the design turns it into a second, fully independent management path.

Chain after this change:

```
Browser → Cloudflare Tunnel → envoy-external → oauth2-proxy :4180 (Auth0 OIDC)
        → ttyd 127.0.0.1:7681 (requires X-Forwarded-Email) → claude-session → claude
                                    kubectl → 10.96.0.1:443 (in-cluster, no Omni)
```

## Goals / Non-Goals

**Goals:**
- cc.jiahd.cc can diagnose *and fix* the cluster when Omni is unreachable.
- Access limited to one identity (`jiahdadm@gmail.com`) with real login, not a shared static credential.
- Survive pod restarts/image updates without re-login.
- Pattern reusable for client clusters via jg-cluster-template, opt-in and default-off.

**Non-Goals:**
- Surviving total loss of outbound internet at the remote site (nothing can).
- talosctl from inside the pod (Omni-managed Talos holds the credentials; Omni remains the Talos-level path).
- Per-user Kubernetes RBAC (single-admin terminal; MCP memory isolation is a separate concern).

## Decisions

1. **In-cluster RBAC, not an embedded kubeconfig.** `kubeconfig-sa` routes through Omni — useless exactly when the rescue path is needed. A ServiceAccount + CRB keeps kubectl working as long as the API server itself is up. **cluster-admin** (user-confirmed 2026-07-26): a rescue terminal that can only read is half a rescue path.
2. **Shared SA `claude-code` defined in jg-base, referenced by name** (`controllers.<instance>.serviceAccount.name`) rather than chart-created per instance — one CRB covers any number of `claude_instances`, and app-template 4.6.2 supports external SA names (verified in chart source).
3. **root (`runAsUser: 0`) instead of fixing the NAS export.** Matches the established cluster rule (NAS NFS exports allow root only). Side benefit: retires the setcap + `allowPrivilegeEscalation` file-capability dance for the network scanners — root's default runtime caps already include NET_RAW and DAC_OVERRIDE. `HOME=/home/claude` pinned via env because uid 0 would otherwise resolve `/root` and orphan the PVC state.
4. **oauth2-proxy sidecar, not Envoy Gateway SecurityPolicy OIDC.** The image's `claude-session` was designed around a fronting auth proxy that injects the user's email; oauth2-proxy provides it plus a file-based email allowlist. Corrected en route: ttyd does **no** CGI-style `HTTP_*` header mapping (the design doc's `HTTP_X_AUTH_REQUEST_EMAIL` was dead code) — the working mechanism is `ttyd --auth-header X-Forwarded-Email`, which surfaces the value as `TTYD_USER` and doubles as a gate (requests without the header are rejected).
5. **ttyd binds `127.0.0.1`, explicitly not `"lo"`.** hostNetwork means `:7681` would otherwise be a LAN-reachable auth bypass. Found in deployment: ttyd resolves an interface *name* to its first non-127 address — on Talos, `lo` carries a `169.254.x.x`, which broke the proxy upstream and the probes. Probes moved to in-pod exec (`/dev/tcp/127.0.0.1/7681`) since kubelet's tcpSocket probe targets the (host) pod IP.
6. **Login persistence via `CLAUDE_CONFIG_DIR=/home/claude/.claude`** — puts `.claude.json` (onboarding/account state) and `.credentials.json` on the existing claude-config PVC instead of the ephemeral overlay; keyring dir mounted from the same PVC via subPath as belt-and-braces.
7. **Reuse the synophoto Auth0 app** (user-confirmed): one dashboard edit (add cc callback/logout/origin URLs), shared tenant gives SSO across jiahd.cc apps. Allowlist is data (`claudecode_allowed_emails`, comma→newline at render time), not Auth0 config.
8. **Everything conditional on `claudecode_auth0_domain`** in the shared template: unset → previous ttyd-basic-auth behavior byte-for-byte; set → OIDC mode. Client clusters are unaffected until they opt in; image changes are env-gated the same way.

## Risks / Trade-offs

- **Auth0 (+ Google) becomes the front-door dependency.** If Auth0 is down, cc.jiahd.cc is locked out; fallback is the Omni path — acceptable since the two paths fail independently.
- **cluster-admin behind a single OIDC identity.** Compromise of the Google account = cluster compromise. Mitigated by the one-email allowlist and Auth0-side MFA options; still strictly better than the previous shared basic-auth credential carrying the same blast radius.
- **Root pod with LAN access and scanners.** Accepted for a single-admin home-ops rescue terminal; client deployments keep `replicas: 0` default (off unless actively supporting).
- **PVC-stored OAuth tokens** (`.credentials.json` on NAS-backed storage) — plaintext at rest on the NAS; consistent with the cluster's existing secret-at-rest posture.
- The lo/169.254.x ttyd behavior is undocumented upstream; pinned by comment in template + entrypoint so it isn't "simplified" back.
