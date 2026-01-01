# MLaaS Lite: Multi-Tenant Machine Learning Platform

![Status](https://img.shields.io/badge/Status-MVP_Complete-success)
![Kubernetes](https://img.shields.io/badge/Orchestration-Kubernetes-blue)
![Backend](https://img.shields.io/badge/Backend-FastAPI_%2B_Celery-green)
![ML Engine](https://img.shields.io/badge/Engine-Argo_Workflows-orange)

> **A self-service Internal Developer Platform (IDP) that allows Data Scientists to train, track, and deploy models to Kubernetes without needing deep DevOps knowledge.**

## 📋 Project Overview

**MLaaS Lite** solves the "throwing code over the wall" problem in ML Engineering. It provides a standardized "Golden Path" where users can submit Python training scripts, have them executed in isolated Kubernetes environments, and deploy the resulting models to scalable APIs with a single click.

### Key Capabilities
*   **Multi-Tenancy:** Automated provisioning of isolated Namespaces (`team-alpha`, `team-omega`) with strict Resource Quotas and LimitRanges.
*   **Workflow Orchestration:** Dynamic generation of DAGs using **Argo Workflows** to manage training pipelines.
*   **Hybrid Cloud Storage:** Seamless integration with **Google Cloud Storage (GCS)** for artifact management.
*   **Async Architecture:** Non-blocking infrastructure provisioning using **Celery & Redis**.
*   **One-Click Serving:** Automated deployment of inference services that hot-load models from GCS.

---

## 🏗 Architecture

```mermaid
graph TD
    User[User / Data Scientist] -->|UI Interaction| Frontend[React Dashboard]
    Frontend -->|REST API| Backend[FastAPI Server]
    
    subgraph "Async Worker Layer"
        Backend -->|Task Queue| Redis[(Redis Broker)]
        Redis -->|Consume Task| Celery[Celery Worker]
    end
    
    subgraph "Kubernetes Cluster (Kind)"
        Celery -->|Provision Namespace| K8sAPI[K8s API Server]
        Backend -->|Submit Workflow| Argo[Argo Controller]
        Argo -->|Spawns| TrainPod[Training Pod]
        
        TrainPod -->|Uploads Model| GCS[(Google Cloud Storage)]
        
        Backend -->|Deploy Request| Deploy[K8s Deployment]
        Deploy -->|Downloads Model| GCS
        Deploy -->|Expose| Service[Inference Service]
```

## 🛠 Tech Stack

### **Frontend**
| Technology | Badge | Usage |
| :--- | :--- | :--- |
| **React** | ![React](https://img.shields.io/badge/react-%2320232a.svg?style=flat&logo=react&logoColor=%2361DAFB) | Single Page Application framework (Vite). |
| **TypeScript** | ![TypeScript](https://img.shields.io/badge/typescript-%23007ACC.svg?style=flat&logo=typescript&logoColor=white) | Type safety for API integration and components. |
| **Tailwind CSS** | ![TailwindCSS](https://img.shields.io/badge/tailwindcss-%2338B2AC.svg?style=flat&logo=tailwind-css&logoColor=white) | Rapid UI styling and layout. |
| **TanStack Query** | ![React Query](https://img.shields.io/badge/-React%20Query-FF4154?style=flat&logo=react%20query&logoColor=white) | Async state management and API caching. |

### **Backend**
| Technology | Badge | Usage |
| :--- | :--- | :--- |
| **FastAPI** | ![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi) | High-performance Python REST API. |
| **Python** | ![Python](https://img.shields.io/badge/python-3670A0?style=flat&logo=python&logoColor=ffdd54) | Core language for backend logic and ML scripts. |
| **Celery** | ![Celery](https://img.shields.io/badge/celery-%23a9cc54.svg?style=flat&logo=celery&logoColor=ddf4a4) | Distributed task queue for non-blocking infra ops. |
| **Redis** | ![Redis](https://img.shields.io/badge/redis-%23DD0031.svg?style=flat&logo=redis&logoColor=white) | Message broker and caching layer. |
| **PostgreSQL** | ![Postgres](https://img.shields.io/badge/postgres-%23316192.svg?style=flat&logo=postgresql&logoColor=white) | Relational database for User/Team/Job metadata. |
| **SQLAlchemy** | ![SQLAlchemy](https://img.shields.io/badge/SqlAlchemy-D71F00?style=flat&logo=sqlalchemy&logoColor=white) | ORM for database interactions. |

### **Infrastructure & DevOps**
| Technology | Badge | Usage |
| :--- | :--- | :--- |
| **Kubernetes** | ![Kubernetes](https://img.shields.io/badge/kubernetes-%23326ce5.svg?style=flat&logo=kubernetes&logoColor=white) | Container orchestration (Kind for local dev). |
| **Docker** | ![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white) | Containerization of ML Base and Serving images. |
| **Argo Workflows** | ![Argo](https://img.shields.io/badge/Argo-DF5A2F?style=flat&logo=argo&logoColor=white) | Workflow engine for orchestrating ML training DAGs. |
| **ArgoCD** | ![ArgoCD](https://img.shields.io/badge/ArgoCD-ef7b4d?style=flat&logo=argo&logoColor=white) | GitOps for declarative infrastructure management. |
| **Google Cloud** | ![GCP](https://img.shields.io/badge/GoogleCloud-%234285F4.svg?style=flat&logo=google-cloud&logoColor=white) | GCS Object Storage for model artifacts. |
| **Nginx** | ![Nginx](https://img.shields.io/badge/nginx-%23009639.svg?style=flat&logo=nginx&logoColor=white) | Ingress Controller for traffic routing. |

## ⚡ Getting Started

Follow these steps to spin up the entire platform locally.

### 📋 Prerequisites
*   **Docker Desktop** (Running)
*   **Kind** (Kubernetes in Docker)
*   **Python 3.9+** & **Node.js 18+**
*   **kubectl** & **helm**
*   **Google Cloud Service Account JSON Key** (with `Storage Object Admin` permissions)

---

### 1. Infrastructure Setup
Start the local Kubernetes cluster and install platform services (Argo, Redis, Postgres, Nginx).

```bash
# Spin up Kind Cluster
make up

# Apply Platform Manifests
kubectl apply -f manifests/infra/
```

### 2. Establish Network Tunnels
Since we are running locally on Kind, we need to forward ports to allow the local Backend to communicate with the Cluster databases.

#### Open a new terminal (Terminal 1) and run:
```bash
kubectl port-forward svc/postgres 5432:5432 &
kubectl port-forward svc/redis 6379:6379 &
# Keep this terminal open!
```

### 3. Backend & Worker Setup
You need two separate terminals for the Python services

#### Terminal 2: The API Server
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start the REST API
uvicorn main:app --reload
```
#### Terminal 3: The Async Worker (Celery)
This worker handles GCP credentials and namespace provisioning. It requires your Google Cloud Key.
```bash
cd backend
source venv/bin/activate

# Export your GCP Key (Adjust path to where your json file is)
export GCP_SERVICE_ACCOUNT_JSON=$(cat ../.gcp/your-service-account-key.json)

# Start Celery listening to the infrastructure queue
celery -A worker worker --loglevel=info -Q infra-queue,celery
```

### 4. Frontend Setup

#### Terminal 4: The React Dashboard
```bash
cd frontend
npm install
npm run dev
```

### 5. Access the Platform
*   **Main Dashboard**: http://localhost:5173
*   **API Documentation**: http://localhost:8000/docs
*   **Argo Workflows UI**: https://argo.local (Requires hosts file entry: 127.0.0.1 argo.local)

## 🧪 Usage Guide (The Golden Path)

Follow this workflow to train a model and deploy it as a live API.

### 1. Register a Team
*   Open the Dashboard at `http://localhost:5173`.
*   Enter a **Team Name** (e.g., `omega`) and click **Run Job** (or create a dedicated registration form if implemented).
*   **What happens?** The Celery worker provisions a Kubernetes Namespace (`team-omega`), applies Resource Quotas (Max 2 CPUs), and injects your Google Cloud credentials as a Kubernetes Secret.

### 2. Run a Training Job
*   Paste the following Python code into the **ML Job Submission** box. This script trains a simple Logistic Regression model and saves it to the specific path Argo expects.

```python
import os
import joblib
from sklearn.linear_model import LogisticRegression
import numpy as np

print("🚀 Starting Training...")

# 1. Generate Fake Data
X = np.random.rand(100, 5)
y = np.random.randint(2, size=100)

# 2. Train Model
clf = LogisticRegression()
clf.fit(X, y)
print(f"✅ Model Trained! Score: {clf.score(X, y)}")

# 3. Save to Disk (Critical for Artifact Upload)
os.makedirs("/outputs", exist_ok=True)
joblib.dump(clf, "/outputs/model.pkl")

print("💾 Model saved to /outputs/model.pkl")
```

* Click **Run Job**
* **What happens?**
    1. The API submits a workflow to Argo.
    2. Argo spins up a Pod in team-omega.
    3. The code runs, and the resulting model.pkl is automatically uploaded to your Google Cloud Storage bucket.

### 3. Deploy the Model
* Scroll down to the **Model Registry** section in the UI.
* Wait for the new model (e.g., omega-model-v15) to appear.
* Click the purple **Deploy API** button.
* **What happens?** Kubernetes spins up a serving pod that downloads your specific model version from GCS and exposes it via FastAPI.

### 4. Test Predictions
Once the deployment is running, you can talk to it via curl.

1. **Port Forward the Service:**
Find the service name (usually model-{id}) and forward it to your localhost.

```bash
# Check for running services
kubectl get svc -n team-omega

# Forward port (replace model-15 with your actual ID)
kubectl port-forward svc/model-15 -n team-omega 9090:80
```

2. **Send a Prediction Request**
Open a new terminal and send some dummy data:

```bash
curl -X POST "http://localhost:9090/predict" \
     -H "Content-Type: application/json" \
     -d '{"features": [[0.5, 0.5, 0.5, 0.5, 0.5]]}'
```

3. **Expected Response**
```json
{"prediction": [0]}
```

## 🧠 Engineering Challenges & Solutions

### The "Secret Zip" Corruption
**Problem:** Argo Workflows defaults to archiving (tar/gzip) output artifacts. When the inference server tried to load the .pkl file via joblib, it crashed with KeyError: 109 because it was reading a tarball header, not a pickle object.
**Solution:** Configured archive: none in the Jinja2 Workflow Template to ensure raw file uploads to GCS.
### 2. The "Zombie Deployment" Loop
**Problem:** When updating a model, simply deleting the Pods caused the ReplicaSet to spawn them back immediately with the old configuration. Attempting to create a new Deployment over an old one failed with 409 Conflict.
**Solution:** Implemented a strict cleanup routine in the backend that deletes the Deployment and Service objects completely before provisioning the new version.
### 3. Cloud Identity Injection
**Problem:** How to securely allow dynamic namespaces to access a centralized GCP Bucket without hardcoding keys in the image?
**Solution:** Built a Celery task that injects a Kubernetes Secret containing the GCP Service Account JSON into every new Tenant Namespace (team-*) upon registration. The Serving Pods mount this secret as a volume at runtime.

## 🔮 Future Roadmap

The current MVP demonstrates the core "Golden Path" for ML Engineering. The following features are planned to move the platform towards production readiness.

### 🛡️ Security & Governance
- [ ] **OIDC Authentication:** Replace the current dummy login with **Keycloak** or **Auth0** integration to enforce real user identity.
- [ ] **RBAC Implementation:** Implement `ClusterRoles` to restrict Team Alpha from viewing Team Omega's logs or models.
- [ ] **Network Policies:** Use Calico/Cilium to enforce strict network isolation (deny cross-namespace traffic by default).
- [ ] **Secret Management:** Integrate **HashiCorp Vault** or **External Secrets Operator** to stop storing GCP keys in plain Kubernetes Secrets.

### 📊 Observability & Monitoring
- [ ] **Metrics Stack:** Deploy **Prometheus & Grafana** to visualize:
    -   *Cluster Health:* CPU/RAM saturation per node.
    -   *Model Performance:* Request latency (p99) and error rates for serving pods.
- [ ] **Centralized Logging:** Deploy **Loki + Promtail** to aggregate training logs instead of relying on transient Pod logs.
- [ ] **Cost Allocation:** Implement **Kubecost** to track how much money `Team Omega` is spending on cloud resources.

### 🚀 Advanced ML Features
- [ ] **GPU Support:** Configure Kubernetes Node Pools with Nvidia Drivers to allow `nvidia.com/gpu: 1` requests for Deep Learning jobs.
- [ ] **Hyperparameter Tuning:** Integrate **Katib** for automated hyperparameter search.
- [ ] **Interactive Notebooks:** Spawn **JupyterLab** instances inside the user's namespace for exploratory data analysis (EDA).

### ⚡ Scaling & Operations
- [ ] **Serverless Inference:** Implement **KEDA** (Kubernetes Event-driven Autoscaling) to scale serving pods to zero when no traffic is detected.
- [ ] **Canary Deployments:** Use **Argo Rollouts** to gradually shift traffic to new model versions (Blue/Green deployment) rather than instant cutovers.
- [ ] **Spot Instances:** Configure the training node pool to use AWS Spot Instances / GCP Preemptible VMs to reduce compute costs by ~70%.