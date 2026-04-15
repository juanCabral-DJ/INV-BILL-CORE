from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.db.Config import settings


# definir credenciales
db_url = settings.db_connection_url

# crear el motor
engine = create_engine(db_url)

# crear las sesiones
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependencia para FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
