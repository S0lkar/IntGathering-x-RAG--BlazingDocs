from pathlib import Path
from Project import ProjectContext
import os, shutil, pickle, numpy as np, faiss
from sqlalchemy import create_engine, Column, Integer, Text, Boolean, Float
from sqlalchemy.orm import sessionmaker, declarative_base


Base = declarative_base()


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True)
    Pregunta = Column(Text)
    Respuesta = Column(Boolean)
    Detalle = Column(Text)
    Source = Column(Text)
    Confidence = Column(Float)


class Collection:
    
    DefaultDBPath = Path(".", "DEFAULT", "collections")
    
    def __init__(self, P: ProjectContext, AspectName: str):
        self.P = P
        self.ProjectPath = Path(".", P.NAME)
        self.DB_path = Path(".", P.NAME, "collections", AspectName)
        self.Name = AspectName
        
        if not os.path.isfile(self.DB_path):
            shutil.copyfile(Collection.DefaultDBPath / AspectName, self.DB_path)

        sqlite_url = f"sqlite:///{self.DB_path}" # SQLite local
        self.engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.index = faiss.read_index(str(self.ProjectPath / "index.faiss"))

        with open(self.ProjectPath / "file_names.pkl", "rb") as f:
            self.filenames = pickle.load(f)

        with open(self.ProjectPath / "texts.pkl", "rb") as f:
            self.texts = pickle.load(f)

    #! Funcion principal de query, se podria hacer finetunning según el contexto específico
    def __RAGQuery(self, query: str):
        # 1. Obtener embedding de la query
        q_emb = self.P.model.encode([query])
        q_emb = np.array(q_emb).astype("float32")

        # 2. Buscar chunk más cercano
        k = 1  # solo necesitamos el más cercano
        distances, indices = self.index.search(q_emb, k)

        if len(indices[0]) == 0:
            # No hay resultados
            return None, "", "", 0.0

        # 3. Recuperar el chunk y el archivo
        closest_chunk = self.texts[indices[0][0]]
        source_file = self.filenames[indices[0][0]] if self.filenames else ""

        # 4. Calcular confianza (normalizando distancia L2)
        distance = distances[0][0]
        confidence = 1 / (1 + distance)  # cuanto más pequeño el distance, más confianza

        # 5. Decisión True/False según si la distancia es suficientemente baja
        # Se puede establecer un umbral si quieres filtrar matches débiles
        threshold = 0.5  # ajustar según tu caso
        response = confidence > threshold

        return response, closest_chunk, source_file, confidence
    
    def fill_Aspect(self):

        questions = self.session.query(Question).all()

        for q in questions:

            response, detail, source, confidence = self.__RAGQuery(q.Pregunta)

            q.Respuesta = response
            q.Detalle = detail
            q.Source = source
            q.Confidence = confidence

        self.session.commit()
    
    def reset_Aspect(self):
        shutil.copyfile(Collection.DefaultDBPath / self.Name, self.DB_path)

    @staticmethod
    def Create_BaseAspect(AspectName: str) -> None:
        db_path = Collection.DefaultDBPath / AspectName
        db_path.parent.mkdir(parents=True, exist_ok=True)

        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)

    @staticmethod
    def Add_BaseQuestion(AspectName: str, question: str) -> None:
        db_path = Collection.DefaultDBPath / AspectName
        engine = create_engine(f"sqlite:///{db_path}")
        Session = sessionmaker(bind=engine)
        session = Session()

        exists = session.query(Question).filter(Question.Pregunta == question).first()

        if not exists:
            q = Question(
                Pregunta=question,
                Respuesta=False,
                Detalle="",
                Source="",
                Confidence=0.0
            )
            session.add(q)
            session.commit()

        session.close()

    @staticmethod
    def Get_BaseQuestionID(AspectName: str, question: str) -> int:
        db_path = Collection.DefaultDBPath / AspectName
        engine = create_engine(f"sqlite:///{db_path}")
        Session = sessionmaker(bind=engine)
        session = Session()

        q = session.query(Question).filter(Question.Pregunta == question).first()

        session.close()

        return q.id if q else -1

    @staticmethod
    def Delete_BaseQuestion(AspectName: str, question: str | int) -> None:
        db_path = Collection.DefaultDBPath / AspectName
        engine = create_engine(f"sqlite:///{db_path}")
        Session = sessionmaker(bind=engine)
        session = Session()

        if isinstance(question, int):
            qid = question
        else:
            qid = Collection.Get_BaseQuestionID(AspectName, question)

        if qid != -1:
            q = session.query(Question).filter(Question.id == qid).first()
            if q:
                session.delete(q)
                session.commit()

        session.close()

    @staticmethod
    def Modify_BaseQuestionID(AspectName: str, question: str | int, new_question: str) -> None:
        db_path = Collection.DefaultDBPath / AspectName
        engine = create_engine(f"sqlite:///{db_path}")
        Session = sessionmaker(bind=engine)
        session = Session()

        if isinstance(question, int):
            qid = question
        else:
            qid = Collection.Get_BaseQuestionID(AspectName, question)

        if qid != -1:
            q = session.query(Question).filter(Question.id == qid).first()
            if q:
                q.Pregunta = new_question
                session.commit()

        session.close() 

