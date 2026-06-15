from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
from modelos.database import Base
from datetime import date

class Despesa(Base):
    __tablename__ = "despesas"

    id = Column(Integer, primary_key=True, index=True)
    categoria = Column(String, nullable=False)
    descricao = Column(String, nullable=False)
    valor = Column(Float, nullable=False)
    data = Column(Date, default=date.today)
    veiculo_id = Column(Integer, ForeignKey("veiculos.id"), nullable=True)

    veiculo = relationship("Veiculo", backref="despesas")
