cp ./config.gen/cluster.yaml .
cp ./config.gen/nodes.yaml .
#cp ./config.gen/cloudflare-tunnel.json .

test -e $PWD/talos || mkdir $PWD/talos
test -e $PWD/talos/clusterconfig || mkdir $PWD/talos/clusterconfig
cp ./config.gen/*kubeconfig.yaml $KUBECONFIG
cp ./config.gen/*talosconfig.yaml $TALOSCONFIG

#export KUBECONFIG=$PWD/kubeconfig
#export TALOSCONFIG=$PWD/talosconfig
