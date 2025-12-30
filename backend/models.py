from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)

    # Link to a team
    team_id = Column(Integer, ForeignKey("teams.id"))
    team = relationship("Team", back_populates="users")

class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

    # Vital: The K8s Namespace this team owns
    k8s_namespace = Column(String, unique=True)

    # Relationship to users
    users = relationship("User", back_populates="team")