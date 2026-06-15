from sqlalchemy import Column, Integer, String, Float, Boolean
from modelos.database import Base

class Investidor(Base):
    __tablename__ = "investidores"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, nullable=True)
    telefone = Column(String, nullable=True)
    cpf_cnpj = Column(String, nullable=True)
    percentual_comissao = Column(Float, default=20.0)
    ativo = Column(Boolean, default=True)
