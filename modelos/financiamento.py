from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
from modelos.database import Base
from datetime import date

class Financiamento(Base):
    __tablename__ = "financiamentos"

    id = Column(Integer, primary_key=True, index=True)
    veiculo_id = Column(Integer, ForeignKey("veiculos.id"), nullable=False)
    banco = Column(String, nullable=False)
    valor_financiado = Column(Float, nullable=False)
    entrada = Column(Float, default=0.0)
    parcela_mensal = Column(Float, nullable=False)
    total_parcelas = Column(Integer, nullable=False)
    parcelas_pagas = Column(Integer, default=0)
    data_inicio = Column(Date, default=date.today)

    # Trocado de backref para back_populates (evita conflito)
    veiculo = relationship("Veiculo", back_populates="financiamentos")

    @property
    def parcelas_restantes(self):
        return self.total_parcelas - self.parcelas_pagas

    @property
    def quitado(self):
        return self.parcelas_pagas >= self.total_parcelas

    @property
    def total_pago(self):
        return self.parcelas_pagas * self.parcela_mensal

    @property
    def total_devido(self):
        return self.parcelas_restantes * self.parcela_mensal
