# Tasks: cc-rescue-path

> Retroactive — all work implemented and verified 2026-07-26 (Auth0 dashboard step completed by user 2026-07-27).

## 1. Cluster access (kubectl + RBAC)

- [x] 1.1 Add kubectl v1.36.0 (arch-aware) to k8scc Dockerfile (`86e7212`)
- [x] 1.2 jg-base: `rbac.yaml` — SA `claude-code` + ClusterRoleBinding to cluster-admin (`6dedb7f`)
- [x] 1.3 Instances template: `serviceAccount.name: claude-code` (external SA reference)
- [x] 1.4 Verify in pod: `kubectl get nodes`, `kubectl auth can-i '*' '*'` → yes; endpoint `10.96.0.1:443` (no Omni)

## 2. NAS mount (root)

- [x] 2.1 `defaultPodOptions.securityContext` → `runAsUser: 0` / `runAsGroup: 0`; drop runAsNonRoot
- [x] 2.2 Remove setcap/NET_RAW/`allowPrivilegeEscalation` container securityContext (obsolete as root)
- [x] 2.3 Pin `HOME=/home/claude` via env
- [x] 2.4 Verify: `/home/claude/coding` readable, uid 0, HOME correct

## 3. Login persistence

- [x] 3.1 `CLAUDE_CONFIG_DIR=/home/claude/.claude` env (`0ca1818`)
- [x] 3.2 Mount keyring dir from claude-config PVC via subPath
- [x] 3.3 Verify: `.claude.json` + `.credentials.json` on PVC; restart pod → "Welcome back", no re-login
- [x] 3.4 End-to-end: WebSocket to cc.jiahd.cc → `!kubectl get nodes` works in the web terminal

## 4. Auth0 OIDC (replaces ttyd basic auth)

- [x] 4.1 k8scc: env-gated `TTYD_INTERFACE` / `TTYD_AUTH_HEADER`; `claude-session` reads `TTYD_USER` (`e249a9c`)
- [x] 4.2 jg-cluster-template: schema +5 optional fields; cluster-secrets j2 +4 vars (comma→newline for allowlist); sample docs (`e17ed0b`)
- [x] 4.3 jg-base secret: `OAUTH2_PROXY_CLIENT_ID/SECRET/COOKIE_SECRET`, `ALLOWED_EMAILS` (`9ef6e1d`)
- [x] 4.4 Instances template: conditional oauth2-proxy v7.15.3 sidecar, service/route → 4180, exec probes, emails file mount (`8fcba4e`)
- [x] 4.5 jg-jiahd cluster.yaml: Auth0 values (synophoto app reuse), cookie secret generated, allowlist `jiahdadm@gmail.com`
- [x] 4.6 Fix: `TTYD_INTERFACE` `lo` → `127.0.0.1` (ttyd resolves iface name to first non-127 addr; Talos lo carries 169.254.x.x) (`313dafb`)
- [x] 4.7 Auth0 dashboard: add cc.jiahd.cc callback/logout/origin URLs (user)
- [x] 4.8 Verify: `/` and old basic-auth both 302 → Auth0; `/ping` 200; `<node-ip>:7681` refused; user login OK

## 5. Documentation

- [x] 5.1 This OpenSpec change (proposal/design/spec/tasks) + sync `remote-terminal` spec
- [x] 5.2 Update k8scc `web-tty-claudecode.md` to match implementation (TTYD_USER mechanism, root, kubectl, persistence, OIDC mode)
