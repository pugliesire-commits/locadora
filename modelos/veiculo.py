from sqlalchemy import Column, Integer, String, Float
from modelos.database import Base

class Veiculo(Base):
    __tablename__ = "veiculos"

    id           = Column(Integer, primary_key=True, index=True)
    placa        = Column(String, unique=True, index=True)
    marca        = Column(String)
    modelo       = Column(String)
    ano          = Column(Integer)
    categoria    = Column(String)
    cor          = Column(String)
    valor_diaria = Column(Float)
    status       = Column(String, default="Disponível")