from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Endereço do banco de dados (arquivo local)
DATABASE_URL = "sqlite:///./locadora.db"

# Criando a conexão com o banco
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

# Sessão para conversar com o banco
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para criar as tabelas
Base = declarative_base()

# Função que abre e fecha conexão automaticamente
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()