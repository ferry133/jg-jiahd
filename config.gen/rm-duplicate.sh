#############
# Larry: under omni cluster,
# 1) no need to execute: "task bootstrap:talos"
# 2) before "task bootstrap:apps", need to kubectl delete all the coredns/flannel resources in kube-system,
#    including deployment, service, ServiceAccount and configmap.
#
kubectl delete deployment coredns -n kube-system
kubectl delete service kube-dns -n kube-system
kubectl delete serviceaccount coredns -n kube-system
kubectl delete configmap coredns -n kube-system

kubectl delete daemonset.apps kube-flannel  -n kube-system
kubectl delete serviceaccount flannel -n kube-system
kubectl delete configmap kube-flannel-cfg -n kube-system


