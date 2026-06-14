from sqlalchemy import Column, Integer, String, Boolean
from modelos.database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id       = Column(Integer, primary_key=True, index=True)
    nome     = Column(String)
    email    = Column(String, unique=True, index=True)
    senha    = Column(String)  # senha guardada como hash (código secreto)
    perfil   = Column(String, default="atendente")  # admin ou atendente
    ativo    = Column(Boolean, default=True)