cp ./config.gen/cluster.yaml .
cp ./config.gen/nodes.yaml .
cp ./config.gen/cloudflare-tunnel.json .

#mkdir $PWD/talos
#mkdir $PWD/talos/clusterconfig
cp ./config.gen/*kubeconfig.yaml $KUBECONFIG
#cp ./config.gen/*talosconfig.yaml $TALOSCONFIG

#cp ./config.gen/*kubeconfig.yaml ./kubeconfig
#cp ./config.gen/*talosconfig.yaml ./talosconfig

#export KUBECONFIG=$PWD/kubeconfig
#export TALOSCONFIG=$PWD/talosconfig

#############
# Larry: under omni cluster,
# 1) no need to execute: "task bootstrap:talos"
# 2) before "task bootstrap:apps", need to kubectl delete all the coredns resources in kube-system, including deployment, service, ServiceAccount and configmap.
#