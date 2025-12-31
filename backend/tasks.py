from worker import celery_app
from sqlalchemy.orm import Session
from database import SessionLocal
import k8s_service
import os

# This decorator turns a pythong function into a Background Job
@celery_app.task(name="tasks.provision_team")
def provision_team(team_name: str, team_id: int):
    print(f"🚀 [Worker] Starting provisioning for {team_name}...")
    
    # We must create a new DB session because this runs in a separate thread/process
    db: Session = SessionLocal()
    
    try:
        # 1. Create Namespace
        k8s_ns = k8s_service.create_team_namespace(team_name)
        
        # 2. Apply Governance (Quotas/Limits)
        k8s_service.create_resource_quota(k8s_ns)
        k8s_service.create_limit_range(k8s_ns)
        
        # 3. Inject GCP Credentials
        # The Worker Process MUST have the GCP_SERVICE_ACCOUNT_JSON env var set!
        k8s_service.create_gcp_secret(k8s_ns)
        
        print(f"✅ [Worker] Successfully provisioned {team_name}")
        
    except Exception as e:
        print(f"❌ [Worker] Failed to provision {team_name}: {e}")
        # Future: Update DB status to 'FAILED' here
    finally:
        db.close()