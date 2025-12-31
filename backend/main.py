from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import models
import database
import tasks
import k8s_service
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime



# Initialize DB
try:
    models.Base.metadata.create_all(bind=database.engine)
except:
    print("⚠️ DB Connection failed on startup. Is the tunnel running?")

app = FastAPI(title="MLaaS Platform API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # The address of your React App
    allow_credentials=True,
    allow_methods=["*"], # Allow POST, GET, etc.
    allow_headers=["*"],
)


class TeamCreate(BaseModel):
    team_name: str
    admin_email: str
    password: str


@app.post("/register")
def register_team(team_data: TeamCreate, db: Session = Depends(database.get_db)):
    # 1. Check existing
    existing = db.query(models.Team).filter(models.Team.name == team_data.team_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Team already exists")

    # 2. Save to DB (Status: PENDING)
    standard_ns = f"team-{team_data.team_name}"
    
    new_team = models.Team(name=team_data.team_name, k8s_namespace=standard_ns)
    db.add(new_team)
    db.commit()
    db.refresh(new_team)

    new_user = models.User(
        email=team_data.admin_email, 
        hashed_password=team_data.password, 
        team_id=new_team.id
    )
    db.add(new_user)
    db.commit()

    # 3. Trigger Async Task
    # .delay() returns immediately. It does NOT wait for the function to finish.
    tasks.provision_team.delay(team_data.team_name, new_team.id)

    return {
        "status": "accepted", 
        "message": "Provisioning started in background", 
        "namespace": standard_ns
    }





class JobSubmit(BaseModel):
    team_name: str
    python_code: str

@app.post("/jobs")
def submit_job(job_data: JobSubmit, db: Session = Depends(database.get_db)):
    # 1. Verify Team
    team = db.query(models.Team).filter(models.Team.name == job_data.team_name).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
        
    # 2. Create DB Record
    new_job = models.Job(team_id=team.id, status="SUBMITTED")
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    
    # 3. Submit to K8s
    # (For Day 10, we do this synchronously. In Prod, move to Celery!)
    try:
        workflow_name = k8s_service.submit_workflow(
            team_name=team.name,
            job_id=new_job.id,
            python_code=job_data.python_code
        )
        
        # 4. Update DB with Workflow Name
        new_job.argo_workflow_name = workflow_name

        s3_path = f"{team.name}/{new_job.id}/model.pkl"
        
        new_model = models.Model(
            name=f"{team.name}-model-v{new_job.id}", # Simple versioning strategy
            s3_path=s3_path,
            job_id=new_job.id,
            team_id=team.id,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        db.add(new_model)

        db.commit()
        
        return {"status": "submitted", "job_id": new_job.id, "workflow": workflow_name}
        
    except Exception as e:
        db.delete(new_job) # Cleanup
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173", # <--- ADD THIS LINE
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/jobs")
def list_jobs(db: Session = Depends(database.get_db)):
    # Return latest jobs first
    jobs = db.query(models.Job).order_by(models.Job.id.desc()).all()
    return jobs

@app.get("/jobs/{job_id}/logs")
def get_job_logs(job_id: int, db: Session = Depends(database.get_db)):
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get the team to know the namespace
    team = db.query(models.Team).filter(models.Team.id == job.team_id).first()
    
    logs = k8s_service.get_job_logs(job.argo_workflow_name, team.k8s_namespace)
    return {"logs": logs}

@app.get("/models")
def list_models(db: Session = Depends(database.get_db)):
    return db.query(models.Model).order_by(models.Model.id.desc()).all()