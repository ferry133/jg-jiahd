# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

A personal Kubernetes home-ops cluster (`jiahd.cc`) running on [Talos Linux](https://github.com/siderolabs/talos) managed via [Omni](https://omni.janncot.com). Flux CD GitOps syncs the `kubernetes/` directory to the cluster. Configuration is generated from Jinja2 templates in `templates/` using [makejinja](https://github.com/mirkolenz/makejinja), driven by `cluster.yaml` and `nodes.yaml`.

## Tooling

All tools are managed by [mise](https://mise.jdx.dev/) (see `.mise.toml`). Workflow automation uses [Task](https://taskfile.dev/) (see `Taskfile.yaml` and `.taskfiles/`).

```sh
mise trust && mise install   # install all tools (first time)
```

Environment variables (`KUBECONFIG`, `SOPS_AGE_KEY_FILE`, `TALOSCONFIG`) are auto-set by mise from root paths.

## Key Task Commands

```sh
task                         # list all tasks
task init                    # initialize cluster.yaml / nodes.yaml / age key / deploy key
task configure               # validate schemas → render templates → encrypt secrets → validate configs
task reconcile               # force Flux to sync git → cluster

task bootstrap:talos         # bootstrap a new Talos cluster from talconfig.yaml
task bootstrap:apps          # install Flux and base apps into a running cluster

task talos:apply-node IP=<ip>          # apply Talos config to one node
task talos:upgrade-node IP=<ip>        # upgrade Talos on one node
task talos:upgrade-k8s                 # upgrade Kubernetes version
task talos:reset                       # wipe cluster (destructive!)

task template:debug          # kubectl get on common resources across all namespaces
task template:tidy           # archive template scaffolding after cluster is live
task template:reset          # remove all generated bootstrap/kubernetes/talos dirs (destructive!)
```

## Repository Layout

```
cluster.yaml / nodes.yaml    # primary cluster config inputs (gitignored sample files)
templates/                   # Jinja2 templates rendered by makejinja
  config/                    # bootstrap/, kubernetes/, talos/ output templates
  overrides/                 # partial overrides
  scripts/plugin.py          # makejinja plugin
makejinja.toml               # makejinja config (inputs, output, delimiters)
.taskfiles/                  # Task includes: bootstrap, talos, template
kubernetes/
  flux/cluster/              # Flux entrypoint (ks.yaml)
  apps/                      # App HelmReleases organized by namespace
    cert-manager/
    claude/claude-code/      # Claude Code web terminal deployment
    network/                 # envoy-gateway, cloudflare-tunnel, k8s-gateway, external-dns
    storage/
  components/sops/           # Flux SOPS decryption component
talos/                       # talhelper config (talconfig.yaml, talenv.yaml, talsecret.sops.yaml)
bootstrap/                   # helmfile.d for initial Flux bootstrap
docker/claude-code/          # Custom Docker image: Claude Code CLI + ttyd web terminal
scripts/                     # bootstrap-apps.sh and libs
```

## Template System

`task configure` runs the full pipeline:
1. **Schema validation** — `cue vet` against `.taskfiles/template/resources/*.schema.cue`
2. **Rendering** — `makejinja` reads `cluster.yaml` + `nodes.yaml`, outputs into `kubernetes/`, `talos/`, `bootstrap/`
3. **Encryption** — `sops` encrypts any `*.sops.*` files that are not yet encrypted
4. **Validation** — `kubeconform` checks Kubernetes manifests; `talhelper validate` checks Talos config

Jinja2 delimiters are non-standard (to avoid YAML conflicts): `#{…}#` for variables, `#%…%#` for blocks.

## Secrets Management

Secrets use [SOPS](https://github.com/getsops/sops) + [age](https://github.com/FiloSottile/age). The age private key lives at `./age.key` (local only, never committed). Rules in `.sops.yaml`:
- `talos/*.sops.yaml` — full file encrypted
- `bootstrap/*.sops.yaml` and `kubernetes/*.sops.yaml` — only `data`/`stringData` keys encrypted

Flux decrypts secrets at runtime using the `kubernetes/components/sops/` component (referenced in Kustomizations).

## Claude Code App (`docker/claude-code/`)

A custom Docker image running Claude Code CLI inside a [ttyd](https://github.com/tsl0922/ttyd) web terminal. Built and pushed to `ghcr.io/ferry133/claude-code` via GitHub Actions on pushes to `docker/claude-code/**`. The image runs as non-root user `claude` and sets up D-Bus + GNOME Keyring for OAuth credential storage.

The Kubernetes deployment (`kubernetes/apps/claude/claude-code/app/helmrelease.yaml`) mounts two PVCs: `.claude/` config (5Gi) and `workspace/` (20Gi) on `sc-nas` storage class.

## Flux GitOps Structure

Flux watches the `main` branch. The entrypoint is `kubernetes/flux/cluster/ks.yaml` which bootstraps all namespace Kustomizations. Each app namespace has a `kustomization.yaml` referencing its resources. `HelmRelease` resources pull charts from OCI repositories.

Use `envoy-external` gateway on `HTTPRoutes` for internet-facing apps; `envoy-internal` for LAN-only apps.

## Cluster Network

| Purpose | Address |
|---|---|
| Kube API | `10.9.9.2` |
| k8s-gateway (split DNS) | `10.9.9.3` |
| Internal gateway | `10.9.9.4` |
| External/Cloudflare gateway | `10.9.9.5` |
| Node CIDR | `10.9.9.0/24` |
| Pod CIDR | `10.42.0.0/16` |
| Service CIDR | `10.96.0.0/16` |

Domain: `jiahd.cc` (Cloudflare). Split DNS: home DNS server forwards `jiahd.cc` to `10.9.9.3`.
