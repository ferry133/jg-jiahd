---
description: Claude Code docker app details — loaded when working in docker/
globs: ["docker/**"]
---

## Claude Code App (`docker/claude-code/`)

Custom Docker image: Claude Code CLI + [ttyd](https://github.com/tsl0922/ttyd) web terminal.
- Pushed to `ghcr.io/ferry133/claude-code` via GitHub Actions on pushes to `docker/claude-code/**`
- Runs as non-root user `claude`; sets up D-Bus + GNOME Keyring for OAuth credential storage

Kubernetes deployment: `kubernetes/apps/claude/claude-code/app/helmrelease.yaml`
- Two PVCs: `.claude/` config (5Gi) and `workspace/` (20Gi) on `sc-nas` storage class
