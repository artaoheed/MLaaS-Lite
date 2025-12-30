from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import models, database, k8s_service

# app = FastAPI(title="MLaaS Platform API", version="0.1.0")

# @app.get("/")
# def read_root():
#     return {"status": "active", "service": "mlaas-backend"}

# @app.get("/health")
# def health_check():
#     return {"status": "ok"}


# Create tables (shortcut for dev, use alembic in prod)
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

class TeamCreate(BaseModel):
    team_name: str
    admin_email: str
    password: str

@app.post("/register")
def register_team(team_data: TeamCreate, db: Session = Depends(database.get_db)):
    # 1. Check if team exists
    existing_team = db.query(models.Team).filter(models.Team.name == team_data.team_name).first()
    if existing_team:
        raise HTTPException(status_code=400, detail="Team already exists")

    # 2. PROVISION INFRASTRUCTURE (The Magic)
    # This calls Kubernetes API
    try:
        k8s_ns = k8s_service.create_team_namespace(team_data.team_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to provision namespace: {str(e)}")

    # 3. Save to DB
    new_team = models.Team(name=team_data.team_name, k8s_namespace=k8s_ns)
    db.add(new_team)
    db.commit()
    db.refresh(new_team)

    new_user = models.User(
        email=team_data.admin_email, 
        hashed_password=team_data.password, # Hash this in real life!
        team_id=new_team.id
    )
    db.add(new_user)
    db.commit()

    return {"status": "created", "team": new_team.name, "namespace": k8s_ns}