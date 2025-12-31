from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import models
import database
import tasks # <--- Import the tasks

# Initialize DB
try:
    models.Base.metadata.create_all(bind=database.engine)
except:
    print("⚠️ DB Connection failed on startup. Is the tunnel running?")

app = FastAPI(title="MLaaS Platform API", version="0.1.0")

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