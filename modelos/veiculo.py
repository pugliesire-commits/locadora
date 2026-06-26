from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from modelos.database import Base

class Veiculo(Base):
    __tablename__ = "veiculos"
    id            = Column(Integer, primary_key=True, index=True)
    marca         = Column(String(50), nullable=False)
    modelo        = Column(String(50), nullable=False)
    ano           = Column(Integer, nullable=False)
    placa         = Column(String(10), unique=True, nullable=False)
    cor           = Column(String(30), nullable=True)
    categoria     = Column(String(30), nullable=True)
    chassi        = Column(String(50), nullable=True)
    renavam       = Column(String(20), nullable=True)
    quilometragem = Column(Float, default=0.0)
    status        = Column(String(20), default="Disponível")
    valor_diaria  = Column(Float, nullable=False)
    valor_mercado = Column(Float, nullable=True)
    investidor_id = Column(Integer, ForeignKey("investidores.id"), nullable=True)
    locacoes              = relationship("Locacao", back_populates="veiculo")
    financiamentos        = relationship("Financiamento", back_populates="veiculo")
    lancamentos_investidor = relationship("LancamentoInvestidor", back_populates="veiculo")
    investidor            = relationship("Investidor", back_populates="veiculos")
