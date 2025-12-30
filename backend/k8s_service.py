from kubernetes import client, config
import os

# Load kubeconfig. 
# If running locally, uses ~/.kube/config. 
# If running inside cluster, use config.load_incluster_config()
try:
    config.load_kube_config()
except:
    config.load_incluster_config()

v1 = client.CoreV1Api()

def create_team_namespace(team_name: str):
    """
    Creates a Namespace in Kubernetes for the new team.
    Format: team-{team_name}
    """
    namespace_name = f"team-{team_name}"
    
    # 1. Check if exists
    try:
        v1.read_namespace(name=namespace_name)
        return namespace_name # Already exists
    except client.exceptions.ApiException:
        pass # Does not exist, proceed

    # 2. Create Namespace Object
    ns = client.V1Namespace(
        metadata=client.V1ObjectMeta(
            name=namespace_name,
            labels={"type": "tenant-team"}
        )
    )
    
    # 3. Send to API
    v1.create_namespace(body=ns)
    print(f"✅ Created Kubernetes Namespace: {namespace_name}")
    
    return namespace_name