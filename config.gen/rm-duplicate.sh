#############
# Larry: under omni cluster,
# 1) no need to execute: "task bootstrap:talos"
# 2) before "task bootstrap:apps", need to:
#   A) In this source code, search service cidr "10.43" which should be changed to 10.96. (Omni cluster uses 10.96 as default service cidr, while the default in kubeadm is 10.43)
#   B) kubectl delete all the coredns resources in kube-system, including deployment, service, ServiceAccount and configmap.
#    and, temporarily disable:
#   C) cilium release inside ./bootstrap/helmfile.d/01-apps.yaml
#   D) ./envoy-gateway/ks.yaml & ./k8s-gateway/ks.yaml inside ./kubernetes/apps/network/kustomization.yaml
#
# 2.B) commmands:
#
kubectl delete deployment coredns -n kube-system
kubectl delete service kube-dns -n kube-system
kubectl delete serviceaccount coredns -n kube-system
kubectl delete configmap coredns -n kube-system




# 3) execute "task bootstrap:apps". Might need to re-execute several times until all the resources are applied successfully.
# 4) Verify the cloudflare-tunnel, cloudflare-tunnel-lan and coredns are working properly. The tunnel status should be "healthy" which indicates outbound connectivity to cloudflare network successfully.

# 5) After the cluster is up and running, now we can:
#   A) resume 2.C), 2.D) setting
#   B) kubectl delete all the flannel, kube-proxy resources in kube-system, including deployment, service, ServiceAccount and configmap.
#   C) then execute "task bootstrap:apps" again to apply the cilium and envoy gateway resources.
#
# 5.B) commmands:
#
kubectl delete -f https://raw.githubusercontent.com/flannel-io/flannel/master/Documentation/kube-flannel.yml
kubectl delete daemonset kube-flannel  -n kube-system
kubectl delete configmap kube-flannel-cfg -n kube-system
kubectl delete serviceaccount flannel -n kube-system
kubectl delete ClusterRole/flannel

kubectl delete daemonset kube-proxy -n kube-system
kubectl delete configmap kube-proxy -n kube-system
kubectl delete serviceaccount kube-proxy -n kube-system







# 2) before "task bootstrap:apps", need to kubectl delete all the coredns/flannel resources in kube-system,
#    including deployment, service, ServiceAccount and configmap.
# 3) search service cidr "10.43" which should be changed to 10.96.
#helm uninstall coredns -n kube-system



#. WARN File does not exist file="/Users/ferry133/coding/jg-t1/bootstrap/github-deploy-key.sops.yaml"
