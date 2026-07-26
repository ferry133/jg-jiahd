# remote-terminal Specification

## Purpose

Defines the browser-accessible in-cluster Claude Code terminal (`cc.jiahd.cc`, claudecode extra) as a management/rescue path for the cluster that is fully independent of Omni — its authentication, cluster access, LAN exposure, and state-persistence guarantees. Created by archiving change `cc-rescue-path`.

## Requirements

### Requirement: Omni-independent management path
The cc web terminal SHALL provide full cluster management (kubectl with cluster-admin) through the Cloudflare Tunnel chain only, with no dependency on Omni, SideroLink, or any inbound connectivity to the cluster's network.

#### Scenario: Omni outage
- **WHEN** Omni (or SideroLink) is unreachable but the cluster and its outbound internet are healthy
- **THEN** an allowed user can open `https://cc.<domain>`, log in, and run kubectl against the in-cluster API endpoint (`10.96.0.1:443`) with cluster-admin rights

#### Scenario: remote NAT
- **WHEN** the cluster sits behind NAT on a network with no port forwarding
- **THEN** cc.<domain> remains reachable, because every hop (cloudflared, SideroLink) is outbound-only

### Requirement: OIDC authentication with email allowlist
Access SHALL be gated by Auth0 OIDC (oauth2-proxy sidecar); only emails in `claudecode_allowed_emails` may pass. Static shared credentials SHALL NOT grant access.

#### Scenario: allowed user
- **WHEN** `jiahdadm@gmail.com` completes Auth0 login
- **THEN** the terminal opens and the session's `CLAUDE_USER_ID` equals the logged-in email (via ttyd `--auth-header` → `TTYD_USER`)

#### Scenario: former basic-auth credential
- **WHEN** a client presents the old ttyd basic-auth credential
- **THEN** it is ignored and the client is redirected (302) to Auth0 login

#### Scenario: unlisted email
- **WHEN** a Google account not in the allowlist completes Auth0 login
- **THEN** oauth2-proxy denies access (403), regardless of Auth0 app membership

### Requirement: no authentication bypass on the LAN
ttyd SHALL listen on `127.0.0.1` only (explicit IP — never an interface name) and SHALL reject requests lacking the proxy-injected `X-Forwarded-Email` header, so the terminal is unreachable except through oauth2-proxy.

#### Scenario: direct LAN access attempt
- **WHEN** a LAN host connects to `<node-ip>:7681`
- **THEN** the connection is refused

### Requirement: full workspace access
The pod SHALL run as root so the root-only NAS NFS coding export (`/home/claude/coding`) is readable/writable, with `HOME=/home/claude` pinned via env.

#### Scenario: NAS mount usable
- **WHEN** a session lists `/home/claude/coding`
- **THEN** the NAS export contents are accessible (not `d---------`)

### Requirement: login survives pod lifecycle
Claude onboarding/credential state SHALL live on the claude-config PVC (`CLAUDE_CONFIG_DIR=/home/claude/.claude`; keyring dir on the same PVC), so pod restarts and image updates do not require re-login.

#### Scenario: pod restart
- **WHEN** the deployment is restarted after a user has logged in to Claude
- **THEN** the next session opens at the Claude prompt without onboarding or login screens

### Requirement: opt-in template mode
In the shared cluster template, OIDC mode SHALL activate only when `claudecode_auth0_domain` is set; otherwise instances SHALL keep ttyd basic-auth behavior unchanged (client clusters unaffected until they opt in).

#### Scenario: cluster without Auth0 fields
- **WHEN** a cluster renders the claudecode instances template with no `claudecode_auth0_*` values
- **THEN** the rendered HelmRelease contains the ttyd basic-auth configuration and no oauth2-proxy sidecar
