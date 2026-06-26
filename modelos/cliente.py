from sqlalchemy import Column, Integer, String
from modelos.database import Base

class Cliente(Base):
    __tablename__ = "clientes"
    id          = Column(Integer, primary_key=True, index=True)
    nome        = Column(String)
    cpf         = Column(String, unique=True, index=True)
    rg          = Column(String)
    cnh         = Column(String, unique=True)
    cnh_cat     = Column(String)
    telefone    = Column(String)
    email       = Column(String)
    estado_civil = Column(String)
    endereco    = Column(String)
    bairro      = Column(String)
    cidade      = Column(String)
    estado      = Column(String)
    cep         = Column(String)
