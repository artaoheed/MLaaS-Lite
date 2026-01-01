from kubernetes import client, config
from jinja2 import Environment, FileSystemLoader
import json
import yaml
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


def create_gcp_secret(namespace: str):
    """
    Injects GCP Service Account credentials so User code can access GCS buckets.
    """
    # 1. Fetch the Master Service Account Key from the Backend's Environment
    # This ensures we don't hardcode sensitive keys in the source code.
    sa_json_content = os.getenv("GCP_SERVICE_ACCOUNT_JSON")
    bucket_name = os.getenv("GCP_BUCKET_NAME", "my-ml-platform-bucket")

    if not sa_json_content:
        print(f"⚠️ WARNING: GCP_SERVICE_ACCOUNT_JSON env var is missing. Secret injection skipped for {namespace}.")
        return

    # 2. Prepare the Secret Data
    # We store the JSON file content and the path where it will be mounted
    data = {
        # The actual content of the JSON key file
        "service-account.json": base64.b64encode(sa_json_content.encode('utf-8')).decode('utf-8'),
        
        # Standard Env Var that Google Client Libraries look for automatically
        "GOOGLE_APPLICATION_CREDENTIALS": base64.b64encode(b"/var/secrets/google/service-account.json").decode('utf-8'),
        
        # The bucket name for the user to use
        "GCS_BUCKET_NAME": base64.b64encode(bucket_name.encode('utf-8')).decode('utf-8')
    }

    # 3. Create the Secret Object
    secret = client.V1Secret(
        metadata=client.V1ObjectMeta(
            name="gcp-sa-creds",  # Renamed from ml-s3-creds to be explicit
            labels={"type": "cloud-credentials"}
        ),
        type="Opaque",
        data=data
    )

    # 4. Apply to Kubernetes
    try:
        v1.create_namespaced_secret(namespace=namespace, body=secret)
        print(f"   └── Injected GCP Secrets (gcp-sa-creds) into {namespace}")
    except client.exceptions.ApiException as e:
        if e.status == 409:
            print(f"   └── Secret already exists in {namespace}")
        else:
            raise e

# Setup Jinja2
template_env = Environment(loader=FileSystemLoader("templates"))

def submit_workflow(team_name: str, job_id: int, python_code: str):
    """
    Generates a Workflow YAML and submits it to Argo.
    """
    namespace = f"team-{team_name}"
    
    # 1. Render Template
    template = template_env.get_template("training-job.yaml.j2")
    manifest_str = template.render(
        safe_job_name=team_name, # Simple sanitization
        namespace=namespace,
        job_id=str(job_id),
        team_name=team_name,
        python_code=python_code
    )
    
    # 2. Convert YAML string to Python Dict
    import yaml
    manifest = yaml.safe_load(manifest_str)
    
    # 3. Submit to K8s (Custom Objects API)
    # Group: argoproj.io, Version: v1alpha1, Plural: workflows
    api = client.CustomObjectsApi()
    try:
        response = api.create_namespaced_custom_object(
            group="argoproj.io",
            version="v1alpha1",
            namespace=namespace,
            plural="workflows",
            body=manifest
        )
        print(f"✅ Submitted Workflow: {response['metadata']['name']}")
        return response['metadata']['name']
    except client.exceptions.ApiException as e:
        print(f"❌ Failed to submit workflow: {e}")
        raise e

def get_job_logs(workflow_name: str, namespace: str):
    """
    Finds the main pod for the workflow and reads its logs.
    """
    try:
        # 1. List pods in the namespace labeled with this workflow
        # Argo labels pods with 'workflows.argoproj.io/workflow={workflow_name}'
        label_selector = f"workflows.argoproj.io/workflow={workflow_name}"
        pods = v1.list_namespaced_pod(namespace, label_selector=label_selector)

        if not pods.items:
            return "⏳ Job is starting... No pods found yet."

        # 2. Get the main pod (usually the last one created or the one named 'train')
        # For our simple template, there's usually just one pod doing the work.
        pod_name = pods.items[0].metadata.name
        
        # 3. Read logs
        return v1.read_namespaced_pod_log(name=pod_name, namespace=namespace)
        
    except client.exceptions.ApiException as e:
        return f"⚠️ Could not fetch logs: {e}"

def create_deployment(team_name: str, model_id: int, s3_key: str):
    """
    Creates a Deployment (GCP Version) for the model.
    """
    namespace = f"team-{team_name}"
    app_name = f"model-{model_id}"
    
    # 1. Define Deployment
    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(name=app_name, labels={"app": app_name}),
        spec=client.V1DeploymentSpec(
            replicas=1,
            selector=client.V1LabelSelector(match_labels={"app": app_name}),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": app_name}),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="serving-container",
                            image="ml-serving:v1",
                            image_pull_policy="Never",
                            ports=[client.V1ContainerPort(container_port=80)],
                            env=[
                                # Tell the app which file to download
                                client.V1EnvVar(name="MODEL_S3_KEY", value=s3_key),
                                
                                # 1. Point Google Library to the mounted key
                                client.V1EnvVar(name="GOOGLE_APPLICATION_CREDENTIALS", value="/var/secrets/google/service-account.json"),
                                
                                # 2. Get Bucket Name from the Secret (or hardcode if you prefer)
                                client.V1EnvVar(name="GCP_BUCKET_NAME", value_from=client.V1EnvVarSource(secret_key_ref=client.V1SecretKeySelector(name="gcp-sa-creds", key="GCS_BUCKET_NAME")))
                            ],
                            # 3. MOUNT THE SECRET AS A FILE
                            volume_mounts=[
                                client.V1VolumeMount(
                                    name="gcp-creds",
                                    mount_path="/var/secrets/google",
                                    read_only=True
                                )
                            ]
                        )
                    ],
                    # 4. DEFINE THE VOLUME
                    volumes=[
                        client.V1Volume(
                            name="gcp-creds",
                            secret=client.V1SecretVolumeSource(secret_name="gcp-sa-creds")
                        )
                    ]
                )
            )
        )
    )
    
    # 2. Define Service (ClusterIP) - SAME AS BEFORE
    service = client.V1Service(
        metadata=client.V1ObjectMeta(name=app_name),
        spec=client.V1ServiceSpec(
            selector={"app": app_name},
            ports=[client.V1ServicePort(port=80, target_port=80)]
        )
    )
    
    # 3. Apply
    app_api = client.AppsV1Api()
    core_api = client.CoreV1Api()
    
    # Check if exists to avoid error
    try:
        app_api.create_namespaced_deployment(namespace, deployment)
        core_api.create_namespaced_service(namespace, service)
        print(f"✅ Deployed {app_name} in {namespace}")
    except Exception as e:
        print(f"⚠️ Deployment might already exist: {e}")

    return app_name

