from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date
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

    # Relacionamentos
    cliente = relationship("Cliente")
    veiculo = relationship("Veiculo")