from sqlalchemy import Column, Integer, String, Float, Date, Text, TIMESTAMP
from sqlalchemy.sql import func
from modelos.database import Base

class ExclusaoParcela(Base):
    __tablename__ = "exclusoes_parcelas"
    id = Column(Integer, primary_key=True, index=True)
    parcela_id = Column(Integer, nullable=True)
    locacao_id = Column(Integer, nullable=True)
    numero = Column(Integer, nullable=True)
    data_vencimento = Column(Date, nullable=True)
    valor = Column(Float, nullable=True)
    motivo = Column(Text, nullable=False)
    excluido_em = Column(TIMESTAMP, server_default=func.now())
