# CLAUDE.md — jg-jiahd cluster

## ⚠️ 新增或修改 Extra App 時的三 Repo Checklist

在此 repo 變更 `cluster.yaml`（新增 extras、新增 secret 欄位）時，**必須同步更新另外兩個 repo**：

1. **`jg-base`** — 新增 `kubernetes/apps/extras/<ns>/<app>/` manifests（ks.yaml + app/）
2. **`jg-cluster-template`** — 同步更新：
   - `.taskfiles/template/resources/cluster.schema.cue`（加 optional 欄位）
   - `templates/config/kubernetes/components/sops/cluster-secrets.sops.yaml.j2`（加 VAR 行）
   - `cluster.sample.yaml`（加文件說明）
3. **此 repo（jg-jiahd）** — `cluster.yaml` 填值 → `task configure --yes` → commit & push

完整 checklist 見 `jg-cluster-template/CLAUDE.md`。

---

## kubectl Access

**Always use `kubeconfig-sa`, never `kubeconfig`.**

```sh
kubectl --kubeconfig ~/coding/jg-jiahd/kubeconfig-sa <command>
# or
export KUBECONFIG=~/coding/jg-jiahd/kubeconfig-sa
```

- `kubeconfig` requires OIDC browser auth — cannot be used non-interactively.
- `kubeconfig-sa` has an embedded Omni SA token (SA: `claude-code@serviceaccount.omni.sidero.dev`, Admin, valid ~1 year from 2026-05-13).

## omnictl Access

Requires port-forward (Cloudflare/Envoy terminates gRPC streams):

```sh
KUBECONFIG=~/coding/jcom/kubeconfig kubectl port-forward -n omni svc/omni 18080:8080 &
source ~/.config/omni/env   # loads OMNI_ENDPOINT + OMNI_SERVICE_ACCOUNT_KEY
omnictl <command>
```
