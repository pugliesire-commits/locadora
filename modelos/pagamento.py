from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from modelos.database import Base
from datetime import datetime
import enum

class FormaPagamento(str, enum.Enum):
    pix = "pix"
    cartao_debito = "cartao_debito"
    cartao_credito = "cartao_credito"
    dinheiro = "dinheiro"
    transferencia = "transferencia"

class StatusPagamento(str, enum.Enum):
    pendente = "pendente"
    pago = "pago"
    parcial = "parcial"

class Pagamento(Base):
    __tablename__ = "pagamentos"
    id = Column(Integer, primary_key=True, index=True)
    locacao_id = Column(Integer, ForeignKey("locacoes.id"), nullable=False)
    valor_total = Column(Float, nullable=False)
    valor_pago = Column(Float, default=0.0)
    valor_pendente = Column(Float, default=0.0)
    forma_pagamento = Column(Enum(FormaPagamento), nullable=False)
    status = Column(Enum(StatusPagamento), default=StatusPagamento.pendente)
    data_pagamento = Column(DateTime, default=datetime.utcnow)
    observacao = Column(String, nullable=True)
    locacao = relationship("Locacao", back_populates="pagamentos")

class CobrancaExtra(Base):
    __tablename__ = "cobrancas_extras"
    id = Column(Integer, primary_key=True, index=True)
    locacao_id = Column(Integer, ForeignKey("locacoes.id"), nullable=False)
    tipo = Column(String, nullable=False)
    descricao = Column(String, nullable=True)
    valor = Column(Float, nullable=False)
    data = Column(DateTime, default=datetime.utcnow)
    locacao = relationship("Locacao", back_populates="cobrancas_extras")
