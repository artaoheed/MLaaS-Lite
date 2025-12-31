from celery import Celery
import os

# 1. Configuration
# If we are local, use localhost. If we are in K8s (later), use the service DNS.
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "platform_redis_password")
REDIS_PORT = "6379"

# 2. Connection String
BROKER_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/0"

# 3. Initialize App
celery_app = Celery(
    "worker",
    broker=BROKER_URL,
    backend=BROKER_URL,
    include=["tasks"]
)

# 4. Route tasks to a specific queue (optional but good practice)
celery_app.conf.task_routes = {
    "tasks.provision_team": "infra-queue"
}