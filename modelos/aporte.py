from sqlalchemy import Column, Integer, String, Float, Date
from modelos.database import Base
from datetime import date

class Aporte(Base):
    __tablename__ = "aportes"
    id = Column(Integer, primary_key=True, index=True)
    categoria = Column(String, nullable=False)
    descricao = Column(String, nullable=False)
    valor = Column(Float, nullable=False)
    data = Column(Date, default=date.today)
