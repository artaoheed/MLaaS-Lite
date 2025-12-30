from kubernetes import client, config
import base64
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


def create_resource_quota(namespace: str):
    """
    Limits the total aggregate resources the namespace can consume.
    """
    quota = client.V1ResourceQuota(
        metadata=client.V1ObjectMeta(name="team-quota"),
        spec=client.V1ResourceQuotaSpec(
            hard={
                "requests.cpu": "2",          # Max 2 CPUs total reserved
                "requests.memory": "4Gi",     # Max 4GB RAM total reserved
                "limits.cpu": "4",            # Max 4 CPUs bursting
                "limits.memory": "8Gi",       # Max 8GB RAM bursting
                "pods": "10"                  # Max 10 pods
            }
        )
    )
    v1.create_namespaced_resource_quota(namespace=namespace, body=quota)
    print(f"   └── Applied ResourceQuota to {namespace}")


def create_limit_range(namespace: str):
    """
    Sets default requests/limits if the user forgets to specify them.
    Prevents 'tiny' pods or 'unbounded' pods.
    """
    limit_range = client.V1LimitRange(
        metadata=client.V1ObjectMeta(name="team-defaults"),
        spec=client.V1LimitRangeSpec(
            limits=[
                client.V1LimitRangeItem(
                    type="Container",
                    default={"cpu": "500m", "memory": "512Mi"},
                    default_request={"cpu": "250m", "memory": "256Mi"}
                )
            ]
        )
    )
    v1.create_namespaced_limit_range(namespace=namespace, body=limit_range)
    print(f"   └── Applied LimitRange to {namespace}")