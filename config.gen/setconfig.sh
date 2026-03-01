mkdir $PWD/talos/clusterconfig
cp ./config.gen/*kubeconfig.yaml $KUBECONFIG
cp ./config.gen/*talosconfig.yaml $TALOSCONFIG

#cp ./config.gen/*kubeconfig.yaml ./kubeconfig
#cp ./config.gen/*talosconfig.yaml ./talosconfig

#export KUBECONFIG=$PWD/kubeconfig
#export TALOSCONFIG=$PWD/talosconfig

