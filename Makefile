CLUSTER_NAME := mlaas-cluster

.PHONY: up down cluster-info

# Spin up the cluster using the config

up:
	kind create cluster --name $(CLUSTER_NAME) --config infra/dev/kind-config.yaml
	@echo "Waiting for cluster to be ready..."
	kubectl wait --for=condition=Ready nodes --all --timeout=600s
	@echo "Cluster is up! Context switched to kind - $(CLUSTER_NAME)"

# Tear down the cluster
down:
	kind delete cluster --name $(CLUSTER_NAME)
	@echo "Cluster $(CLUSTER_NAME) has been deleted."

# Check status
cluster-info:
	kubectl cluster-info --context kind-$(CLUSTER_NAME)
	kubectl get nodes -o wide


