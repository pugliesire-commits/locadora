from sqlalchemy import Column, Integer, Float, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from modelos.database import Base
from datetime import date

class LancamentoInvestidor(Base):
    __tablename__ = "lancamentos_investidor"

    id = Column(Integer, primary_key=True, index=True)

    # De qual investidor é esse lançamento?
    investidor_id = Column(Integer, ForeignKey("investidores.id"), nullable=False)

    # De qual carro é esse lançamento?
    veiculo_id = Column(Integer, ForeignKey("veiculos.id"), nullable=False)

    # Qual mês/ano esse lançamento se refere?
    mes_referencia = Column(String(7), nullable=False)  # Exemplo: "2025-06"

    # Os números do mês
    receita_total = Column(Float, default=0.0)        # Dinheiro que entrou
    aportes = Column(Float, default=0.0)              # Dinheiro investido no mês
    despesas_total = Column(Float, default=0.0)       # Dinheiro que saiu
    parcelas_financiamento = Column(Float, default=0.0)  # Parcelas do carro (se financiado)

    # Resultado calculado automaticamente
    lucro_liquido = Column(Float, default=0.0)        # Receita + Aportes - Despesas - Parcelas
    percentual_comissao = Column(Float, default=0.0)  # % que o investidor recebe
    valor_comissao = Column(Float, default=0.0)       # Valor em R$ que vai para o investidor

    # Observações (opcional)
    observacao = Column(String(500), nullable=True)

    # Data em que esse lançamento foi criado
    criado_em = Column(Date, default=date.today)

    # Ligações com outras tabelas
    investidor = relationship("Investidor", back_populates="lancamentos")
    veiculo = relationship("Veiculo", back_populates="lancamentos_investidor")
