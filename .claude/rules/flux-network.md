---
description: Flux GitOps structure and cluster network addresses — loaded when working in kubernetes/
globs: ["kubernetes/**"]
---

## Flux GitOps Structure

Flux watches the `main` branch. Entrypoint: `kubernetes/flux/cluster/ks.yaml` → bootstraps all namespace Kustomizations. Each app namespace has a `kustomization.yaml` referencing its resources. `HelmRelease` resources pull from OCI repositories.

**Gateway rule:** Use `envoy-external` on `HTTPRoutes` for internet-facing apps; `envoy-internal` for LAN-only.

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
