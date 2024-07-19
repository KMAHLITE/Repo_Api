from fastapi import FastAPI, Depends, HTTPException
from typing import List
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# Configuration de la base de données
DATABASE_URL = "postgresql://postgres:Alphasenycamara224@localhost:5432/apiutilisateur"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Modèle de la base de données
class Utilisateur(Base):
    __tablename__ = "utilisateur"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True)
    password = Column(String, unique=True, index=True)

# Création des tables
Base.metadata.create_all(bind=engine)

# Schéma Pydantic
class UtilisateurCreate(BaseModel):
    email: str
    password: str

class UtilisateurUpdate(BaseModel):
    email: str
    password: str

# Initialisation de l'application FastAPI
app = FastAPI()

# Configuration du middleware CORS
orig_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=orig_origins,  # Liste des origines autorisées
    allow_credentials=False,
    allow_methods=["*"],  # Autoriser toutes les méthodes HTTP (GET, POST, etc.)
    allow_headers=["*"],  # Autoriser tous les en-têtes HTTP
)

# Dépendance pour obtenir la session de base de données
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Endpoint de base
@app.get("/")
def read_root():
    return {"message": "Bienvenue à l'API des utilisateurs"}

# Endpoint pour créer un utilisateur
@app.post("/utilisateur/", response_model=UtilisateurCreate)
def ajouter_utilisateur(utilisateur: UtilisateurCreate, db: Session = Depends(get_db)):
    db_utilisateur = Utilisateur(email=utilisateur.email, password=utilisateur.password)
    db.add(db_utilisateur)
    db.commit()
    db.refresh(db_utilisateur)
    return db_utilisateur

# Endpoint pour lire tous les utilisateurs
@app.get("/utilisateurs/", response_model=List[UtilisateurCreate])
def aff_tous(db: Session = Depends(get_db)):
    return db.query(Utilisateur).all()

# Endpoint pour lire un utilisateur par ID
@app.get("/utilisateur/{utilisateur_id}", response_model=UtilisateurCreate)
def aff_par_id(utilisateur_id: int, db: Session = Depends(get_db)):
    utilisateur = db.query(Utilisateur).filter(Utilisateur.id == utilisateur_id).first()
    if utilisateur is None:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    return utilisateur

# Endpoint pour modifier un utilisateur par ID
@app.put("/utilisateur/{utilisateur_id}", response_model=UtilisateurCreate)
def modifier_utilisateur(utilisateur_id: int, utilisateur: UtilisateurUpdate, db: Session = Depends(get_db)):
    db_utilisateur = db.query(Utilisateur).filter(Utilisateur.id == utilisateur_id).first()
    if db_utilisateur is None:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    db_utilisateur.email = utilisateur.email
    db_utilisateur.password = utilisateur.password
    db.commit()
    db.refresh(db_utilisateur)
    return db_utilisateur

# Endpoint pour supprimer un utilisateur par ID
@app.delete("/utilisateur/{utilisateur_id}")
def supprimer_utilisateur(utilisateur_id: int, db: Session = Depends(get_db)):
    db_utilisateur = db.query(Utilisateur).filter(Utilisateur.id == utilisateur_id).first()
    if db_utilisateur is None:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    db.delete(db_utilisateur)
    db.commit()
    return {"message": "Utilisateur supprimé avec succès"}
