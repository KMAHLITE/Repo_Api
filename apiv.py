from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional, List
import jwt

# Configuration de la base de données
DATABASE_URL = "postgresql://postgres:1234@localhost:5432/apiutilisateur"
SECRET_KEY = "mysecretkey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Création du moteur et de la session de base de données
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Création du contexte de hachage de mot de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Classe représentant la table utilisateur dans la base de données
class Utilisateur(Base):
    __tablename__ = "utilisateur"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)

# Création de toutes les tables définies dans les modèles
Base.metadata.create_all(bind=engine)

# Schéma Pydantic pour la création et la mise à jour d'un utilisateur
class UtilisateurCreate(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: str

# Initialisation de l'application FastAPI
app = FastAPI()

# Dépendance pour obtenir la session de base de données
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Fonction pour hacher le mot de passe
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# Fonction pour vérifier le mot de passe
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# Fonction pour créer un JWT
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Fonction pour obtenir l'utilisateur courant à partir du token JWT
def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except jwt.PyJWTError:
        raise credentials_exception
    utilisateur = db.query(Utilisateur).filter(Utilisateur.email == token_data.email).first()
    if utilisateur is None:
        raise credentials_exception
    return utilisateur

@app.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    utilisateur = db.query(Utilisateur).filter(Utilisateur.email == form_data.username).first()
    if not utilisateur or not verify_password(form_data.password, utilisateur.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": utilisateur.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


#---------------------------Un message our vérifier si l'api fonctionne-----------------------------------
@app.get("/")
def read_root():
    return {"message": "Bienvenue à l'API des utilisateurs"}


#-----------------------Pour ajouter les données d'un utilisateur dans la base de donnée-----------------------------------
@app.post("/utilisateur/", response_model=UtilisateurCreate)
def ajouter_utilisateur(utilisateur: UtilisateurCreate, db: Session = Depends(get_db)):
    hashed_password = hash_password(utilisateur.password)
    db_utilisateur = Utilisateur(email=utilisateur.email, password=hashed_password)
    if db.query(Utilisateur).filter(Utilisateur.email == utilisateur.email).first():
        raise HTTPException(status_code=400, detail="Cet email existe dans la base de données")
    db.add(db_utilisateur)
    db.commit()
    db.refresh(db_utilisateur)
    return db_utilisateur


#-----------------------Pour afficher les données de tous les utilisateurs existant dans la base de donnée-----------------------------------
@app.get("/utilisateurs/", response_model=List[UtilisateurCreate])
def aff_tous(db: Session = Depends(get_db)):
    return db.query(Utilisateur).all()


#--------------------Pour afficher les données d'un utilisateur existant dans la base de donnée en fonction de son id-----------------------------------
@app.get("/utilisateur/{utilisateur_id}", response_model=UtilisateurCreate)
def aff_par_id(utilisateur_id: int, db: Session = Depends(get_db)):
    utilisateur = db.query(Utilisateur).filter(Utilisateur.id == utilisateur_id).first()
    if utilisateur is None:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    return utilisateur


#-----------------------Pour modifier les données des utilisateurs dans la base de donnée-----------------------------------
@app.put("/utilisateur/{utilisateur_id}", response_model=UtilisateurCreate)
def modifier_utilisateur(utilisateur_id: int, utilisateur: UtilisateurCreate, db: Session = Depends(get_db)):
    db_utilisateur = db.query(Utilisateur).filter(Utilisateur.id == utilisateur_id).first()
    if db_utilisateur is None:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    db_utilisateur.email = utilisateur.email
    db_utilisateur.password = hash_password(utilisateur.password)
    db.commit()
    db.refresh(db_utilisateur)
    return db_utilisateur


#-----------------------Pour supprimer les données des utilisateurs dans la base de donnée-----------------------------------
@app.delete("/utilisateur/{utilisateur_id}")
def supprimer_utilisateur(utilisateur_id: int, db: Session = Depends(get_db)):
    db_utilisateur = db.query(Utilisateur).filter(Utilisateur.id == utilisateur_id).first()
    if db_utilisateur is None:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    db.delete(db_utilisateur)
    db.commit()
    return {"message": "Utilisateur supprimé avec succès"}
