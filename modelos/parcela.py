from sqlalchemy import Column, Integer, String, Float, Date, Text, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from modelos.database import Base

class Parcela(Base):
    __tablename__ = "parcelas"

    id = Column(Integer, primary_key=True, index=True)
    locacao_id = Column(Integer, ForeignKey("locacoes.id"), nullable=False)
    numero = Column(Integer, nullable=False)
    data_vencimento = Column(Date, nullable=False)
    valor = Column(Float, nullable=False)
    status = Column(String(20), default="pendente")
    data_pagamento = Column(Date, nullable=True)
    forma_pagamento = Column(String(30), nullable=True)
    valor_pago = Column(Float, default=0.0)
    observacao = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Ligação com locação
    locacao = relationship("Locacao", back_populates="parcelas")
