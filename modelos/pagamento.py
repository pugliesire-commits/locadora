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
    locacao_id = Column(Integer,