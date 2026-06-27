from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from modelos.database import Base

class Locacao(Base):
    __tablename__ = "locacoes"
    id             = Column(Integer, primary_key=True, index=True)
    cliente_id     = Column(Integer, ForeignKey("clientes.id"))
    veiculo_id     = Column(Integer, ForeignKey("veiculos.id"))
    data_inicio    = Column(String)
    data_fim       = Column(String)
    dias           = Column(Integer)
    valor_diaria   = Column(Float)
    valor_total    = Column(Float)
    status         = Column(String, default="Ativa")
    observacoes    = Column(String)
    periodo        = Column(String(10), default="diario")
    valor_periodo  = Column(Float, default=0.0)
    contrato_assinado      = Column(Boolean, default=False)
    contrato_assinado_nome = Column(String, nullable=True)
    contrato_assinado_cpf  = Column(String, nullable=True)
    contrato_assinado_em   = Column(DateTime, nullable=True)
    locador_assinado       = Column(Boolean, default=False)
    locador_assinado_nome  = Column(String, nullable=True)
    locador_assinado_em    = Column(DateTime, nullable=True)
    cliente          = relationship("Cliente")
    veiculo          = relationship("Veiculo", back_populates="locacoes")
    pagamentos       = relationship("Pagamento", back_populates="locacao")
    cobrancas_extras = relationship("CobrancaExtra", back_populates="locacao")
    parcelas         = relationship("Parcela", back_populates="locacao")
