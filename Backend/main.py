import os, shutil
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import Boolean, Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from fastapi import UploadFile, File, Form
from pathlib import Path
from dotenv import load_dotenv
from Project import ProjectContext # Gestion de proyectos
from CollectionManager import Collection, Question # Gestion de DBs (RAGs)


#region CONFIG
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("HASH_ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")
DATABASE_URL = os.getenv("DATABASE_SQLITE_SERVER")

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

app = FastAPI()

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
#endregion


#region SQLALCHEMY MODELS
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    disabled = Column(Boolean, default=False)
    role = Column(String, default="user")

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    owner_id = Column(Integer)

Base.metadata.create_all(bind=engine) # Creates tables
#endregion


#region SCHEMAS
class Token(BaseModel):
    access_token: str
    token_type: str


class UserCreate(BaseModel):
    username: str
    full_name: Optional[str]
    email: str
    password: str


class UserOut(BaseModel):
    username: str
    full_name: Optional[str]
    email: str
    disabled: bool
    role: str

    class Config:
        from_attributes = True

#endregion


#region DEPENDENCY DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

#endregion


#region HASHING AND GENERAL SEC

def get_password_hash(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


def authenticate_user(db: Session, username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

#endregion


#region USER_REGISTER
@app.post("/register", response_model=UserOut)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Usuario ya existe")

    hashed_password = get_password_hash(user.password)

    db_user = User(
        username=user.username,
        full_name=user.full_name,
        email=user.email,
        hashed_password=hashed_password,
        role="user"
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user

#endregion


#region LOGIN JWT
@app.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {"access_token": access_token, "token_type": "bearer"}

#endregion


#region WHOAMI


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")

        if username is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()

    if user is None:
        raise credentials_exception

    return user

@app.get("/me", response_model=UserOut)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

#endregion


#region Endpoints Backend

@app.post("/upload-doc")
def upload_doc(name: str = Form(...), db: Session = Depends(get_db), 
               file: UploadFile = File(...), file_type: str = Form(...), current_user: User = Depends(get_current_user)):
    """
    This endpoint, from an identified user, receives a document (PDF, MD, TXT, Excel) and the type it corresponds to
    (a string with the extension).
    When this endpoint receives the document, it stores it in local memory and returns {'status': 'OK'/'NO'} depending on
    whether it could save it.
    """

    allowed = {"pdf", "md", "txt", "xlsx", "xls", "csv"}
    project = db.query(Project).filter(
        Project.name == name,
        Project.owner_id == current_user.id
    ).first()
    
    if not project or (file_type.lower() not in allowed):
        return {"status": "NO"}
    
    raw = Path(".", name, "raw", file.filename)
    plaintext = Path(".", name, "plaintext", file.filename)
    if os.path.isfile(raw):
        return {"status": "Already exists"}
    
    try:
        P = ProjectContext(name)
        with open(raw, "wb") as buffer:
            buffer.write(file.file.read()) # Se guarda el original
        
        shutil.copyfile(raw, plaintext) # Se copia en plain text para ingestarlo
        
        match file_type:
            # md y txt se consideran ya ingestados
            case "pdf":
                P.Ingest_PDF(file.filename)
            case "xlsx":
                P.Ingest_Excel(file.filename)
            case "xls":
                P.Ingest_Excel(file.filename)
            case "csv":
                P.Ingest_Excel(file.filename)
            
        return {"status": "OK"}

    except Exception:
        return {"status": "NO"}


@app.post("/project/new")
def new_project(name: str = Form(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    This endpoint receives a project name, saves the name and associated it to the uploader user. Returns status as well.
    """

    existing = db.query(Project).filter(
        Project.name == name,
        Project.owner_id == current_user.id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Proyecto ya existe")

    project = Project(
        name=name,
        owner_id=current_user.id
    )

    db.add(project)
    db.commit()
    db.refresh(project)
    
    project_path = Path(f"./{name}")
    (project_path / "raw").mkdir(parents=True, exist_ok=True)
    (project_path / "plaintext").mkdir(parents=True, exist_ok=True)
    (project_path / "collections").mkdir(parents=True, exist_ok=True)
    return {"status": "OK", "project": name}


# =========================================================
#  PROJECT
# =========================================================

@app.get("/project/check")
def check_project(name: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    This endpoint receives a project name, returns status ({'status': 'OK'/'NO'}) whether it is associated to the user.
    """

    project = db.query(Project).filter(
        Project.name == name,
        Project.owner_id == current_user.id
    ).first()

    if project:
        return {"status": "OK"}
    return {"status": "NO"}

@app.get("/project/compile")
def RAG_project(name: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    This endpoint receives a project name, returns status ({'status': 'OK'/'NO'}) whether it is associated to the user.
    """

    project = db.query(Project).filter(
        Project.name == name,
        Project.owner_id == current_user.id
    ).first()

    if project:
        P = ProjectContext(name)
        P.GENERATE_RAG()
        
        return {"status": "OK"}
    return {"status": "NO"}


# =========================================================
#  ASPECT
# =========================================================

@app.post("/collections/{collectionname}/create")
def create_base_collection(collectionname: str, current_user: User = Depends(get_current_user)):
    try:
        Collection.Create_BaseCollection(collectionname)
        return {"status": "OK"}
    except Exception:
        return {"status": "NO"}


@app.post("/collections/{collectionname}/add-question")
def add_base_question(
    collectionname: str,
    question: str = Form(...),
    current_user: User = Depends(get_current_user)
):
    try:
        Collection.Add_BaseQuestion(collectionname, question)
        return {"status": "OK"}
    except Exception:
        return {"status": "NO"}


@app.get("/collections/{collectionname}/question-id")
def get_question_id(
    collectionname: str,
    question: str,
    current_user: User = Depends(get_current_user)
):
    try:
        qid = Collection.Get_BaseQuestionID(collectionname, question)
        return {"status": "OK", "id": qid}
    except Exception:
        return {"status": "NO", "id": -1}

@app.delete("/collections/{collectionname}/delete-question")
def delete_base_question(
    collectionname: str,
    question: Optional[str] = None,
    qid: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    try:
        if qid is not None:
            Collection.Delete_BaseQuestion(collectionname, qid)
        elif question is not None:
            Collection.Delete_BaseQuestion(collectionname, question)
        else:
            raise HTTPException(status_code=400, detail="Provide question or qid")

        return {"status": "OK"}
    except Exception:
        return {"status": "NO"}

@app.put("/collections/{collectionname}/modify-question")
def modify_base_question(
    collectionname: str,
    new_question: str = Form(...),
    question: Optional[str] = Form(None),
    qid: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user)
):
    try:
        if qid is not None:
            Collection.Modify_BaseQuestionID(collectionname, qid, new_question)
        elif question is not None:
            Collection.Modify_BaseQuestionID(collectionname, question, new_question)
        else:
            raise HTTPException(status_code=400, detail="Provide question or qid")

        return {"status": "OK"}
    except Exception:
        return {"status": "NO"}

#! (Pending overload unit tests)
@app.get("/project/execute")
def Collection_Fill(name: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = db.query(Project).filter(
        Project.name == name,
        Project.owner_id == current_user.id
    ).first()

    if project:
        P = ProjectContext(name)
        A = Collection(P, "TEST")
        A.fill_Collection()
        
        return {"status": "OK"}
    
    return {"status": "NO"}


@app.get("/collection/data")
def get_collection_data(
    project: str,
    collection: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns all rows of the questions table for a specific project collection.
    """

    # checks the project belongs to the user
    proj = db.query(Project).filter(
        Project.name == project,
        Project.owner_id == current_user.id
    ).first()

    if not proj:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    db_path = Path(".", project, "collections", collection)

    if not db_path.exists():
        raise HTTPException(status_code=404, detail="Collection no encontrado")

    sqlite_url = f"sqlite:///{db_path}"

    engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        rows = session.query(Question).all()

        result = [
            {
                "id": q.id,
                "Pregunta": q.Pregunta,
                "Respuesta": q.Respuesta,
                "Detalle": q.Detalle,
                "Source": q.Source,
                "Confidence": q.Confidence
            }
            for q in rows
        ]

        return result

    finally:
        session.close()

@app.get("/project/collections")
def get_project_collections(
    project: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns all created collections for a project.
    """

    proj = db.query(Project).filter(
        Project.name == project,
        Project.owner_id == current_user.id
    ).first()

    if not proj:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    collections_path = Path(".", project, "collections")

    if not collections_path.exists():
        return []

    collections = [
        f.name for f in collections_path.iterdir()
        if f.is_file()
    ]

    return collections

@app.get("/projects")
def get_user_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns all associated projects to the authenticated user.
    """

    projects = db.query(Project).filter(
        Project.owner_id == current_user.id
    ).all()

    return [
        {
            "id": p.id,
            "name": p.name
        }
        for p in projects
    ]
    
    
#endregion 


