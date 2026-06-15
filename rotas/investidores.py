from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from modelos.database import get_db
from modelos.investidor import Investidor
from modelos.lancamento import LancamentoInvestidor
from modelos.veiculo import Veiculo
from modelos.locacao import Locacao
from modelos.pagamento import Pagamento
from modelos.despesa import Despesa
from modelos.financiamento import Financiamento
from pydantic import BaseModel
from typing import Optional
from datetime import date

router = APIRouter(prefix="/investidores", tags=["Investidores"])

# ---------- Schemas ----------

class InvestidorBase(BaseModel):
    nome: str
    cpf_cnpj: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None
    percentual_comissao: float

class InvestidorCreate(InvestidorBase):
    pass

class LancamentoCreate(BaseModel):
    investidor_id: int
    veiculo_id: int
    mes_referencia: str
    receita_total: float
    aportes: float = 0.0
    despesas_total: float
    parcelas_financiamento: float = 0.0
    observacao: Optional[str] = None

class LancamentoUpdate(BaseModel):
    receita_total: float
    aportes: float = 0.0
    despesas_total: float
    parcelas_financiamento: float = 0.0
    observacao: Optional[str] = None

# ---------- Rotas de Investidores ----------

@router.get("/")
def listar_investidores(db: Session = Depends(get_db)):
    investidores = db.query(Investidor).all()
    resultado = []
    for inv in investidores:
        total_veiculos = db.query(Veiculo).filter(Veiculo.investidor_id == inv.id).count()
        resultado.append({
            "id": inv.id,
            "nome": inv.nome,
            "cpf_cnpj": inv.cpf_cnpj,
            "email": inv.email,
            "telefone": inv.telefone,
            "percentual_comissao": inv.percentual_comissao,
            "ativo": inv.ativo,
            "total_veiculos": total_veiculos
        })
    return resultado

@router.post("/")
def criar_investidor(dados: InvestidorCreate, db: Session = Depends(get_db)):
    novo = Investidor(
        nome=dados.nome,
        cpf_cnpj=dados.cpf_cnpj,
        email=dados.email,
        telefone=dados.telefone,
        percentual_comissao=dados.percentual_comissao
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return {"mensagem": "Investidor cadastrado com sucesso!", "id": novo.id}

@router.get("/{investidor_id}")
def buscar_investidor(investidor_id: int, db: Session = Depends(get_db)):
    inv = db.query(Investidor).filter(Investidor.id == investidor_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investidor não encontrado")
    veiculos = db.query(Veiculo).filter(Veiculo.investidor_id == inv.id).all()
    return {
        "id": inv.id,
        "nome": inv.nome,
        "cpf_cnpj": inv.cpf_cnpj,
        "email": inv.email,
        "telefone": inv.telefone,
        "percentual_comissao": inv.percentual_comissao,
        "ativo": inv.ativo,
        "veiculos": [{"id": v.id, "modelo": v.modelo, "placa": v.placa} for v in veiculos]
    }

@router.put("/{investidor_id}")
def atualizar_investidor(investidor_id: int, dados: InvestidorCreate, db: Session = Depends(get_db)):
    inv = db.query(Investidor).filter(Investidor.id == investidor_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investidor não encontrado")
    inv.nome = dados.nome
    inv.cpf_cnpj = dados.cpf_cnpj
    inv.email = dados.email
    inv.telefone = dados.telefone
    inv.percentual_comissao = dados.percentual_comissao
    db.commit()
    return {"mensagem": "Investidor atualizado com sucesso!"}

@router.delete("/{investidor_id}")
def desativar_investidor(investidor_id: int, db: Session = Depends(get_db)):
    inv = db.query(Investidor).filter(Investidor.id == investidor_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investidor não encontrado")
    inv.ativo = not inv.ativo
    db.commit()
    return {"mensagem": "Status do investidor alterado!"}

# ---------- Rota de pré-cálculo automático ----------

@router.get("/precalculo/{veiculo_id}/{mes_referencia}")
def precalculo_lancamento(veiculo_id: int, mes_referencia: str, db: Session = Depends(get_db)):
    """Busca automaticamente receitas, despesas e parcelas de um veículo num mês."""
    try:
        ano, mes = int(mes_referencia.split("-")[0]), int(mes_referencia.split("-")[1])
    except:
        raise HTTPException(status_code=400, detail="Formato de mês inválido. Use YYYY-MM")

    # Busca locações do veículo nesse mês
    locacoes = db.query(Locacao).filter(
        Locacao.veiculo_id == veiculo_id,
        extract('year', Locacao.data_inicio) == ano,
        extract('month', Locacao.data_inicio) == mes
    ).all()
    locacao_ids = [l.id for l in locacoes]

    # Soma pagamentos recebidos nessas locações
    receita = 0.0
    if locacao_ids:
        from modelos.pagamento import Pagamento
        pags = db.query(Pagamento).filter(Pagamento.locacao_id.in_(locacao_ids)).all()
        receita = sum(p.valor_pago or 0 for p in pags)

    # Busca despesas do veículo nesse mês
    despesas = db.query(Despesa).filter(
        Despesa.veiculo_id == veiculo_id,
        extract('year', Despesa.data) == ano,
        extract('month', Despesa.data) == mes
    ).all()
    total_despesas = sum(d.valor or 0 for d in despesas)

    # Busca parcelas de financiamento do veículo
    financiamento = db.query(Financiamento).filter(
        Financiamento.veiculo_id == veiculo_id,
        Financiamento.quitado == False
    ).first()
    parcela = financiamento.parcela_mensal if financiamento else 0.0

    return {
        "veiculo_id": veiculo_id,
        "mes_referencia": mes_referencia,
        "receita_total": round(receita, 2),
        "despesas_total": round(total_despesas, 2),
        "parcelas_financiamento": round(parcela, 2),
        "total_locacoes": len(locacoes),
        "total_despesas_registradas": len(despesas)
    }

# ---------- Rotas de Lançamentos ----------

@router.post("/lancamentos/novo")
def criar_lancamento(dados: LancamentoCreate, db: Session = Depends(get_db)):
    inv = db.query(Investidor).filter(Investidor.id == dados.investidor_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investidor não encontrado")

    lucro = dados.receita_total + dados.aportes - dados.despesas_total - dados.parcelas_financiamento
    comissao = lucro * (inv.percentual_comissao / 100) if lucro > 0 else 0.0

    novo = LancamentoInvestidor(
        investidor_id=dados.investidor_id,
        veiculo_id=dados.veiculo_id,
        mes_referencia=dados.mes_referencia,
        receita_total=dados.receita_total,
        aportes=dados.aportes,
        despesas_total=dados.despesas_total,
        parcelas_financiamento=dados.parcelas_financiamento,
        lucro_liquido=lucro,
        percentual_comissao=inv.percentual_comissao,
        valor_comissao=comissao,
        observacao=dados.observacao
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return {
        "mensagem": "Lançamento registrado!",
        "id": novo.id,
        "lucro_liquido": lucro,
        "valor_comissao": comissao
    }

@router.put("/lancamentos/{lancamento_id}")
def editar_lancamento(lancamento_id: int, dados: LancamentoUpdate, db: Session = Depends(get_db)):
    """Edita um lançamento já registrado e recalcula a comissão."""
    lanc = db.query(LancamentoInvestidor).filter(LancamentoInvestidor.id == lancamento_id).first()
    if not lanc:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")

    inv = db.query(Investidor).filter(Investidor.id == lanc.investidor_id).first()

    lucro = dados.receita_total + dados.aportes - dados.despesas_total - dados.parcelas_financiamento
    comissao = lucro * (inv.percentual_comissao / 100) if lucro > 0 else 0.0

    lanc.receita_total = dados.receita_total
    lanc.aportes = dados.aportes
    lanc.despesas_total = dados.despesas_total
    lanc.parcelas_financiamento = dados.parcelas_financiamento
    lanc.lucro_liquido = lucro
    lanc.valor_comissao = comissao
    lanc.observacao = dados.observacao
    db.commit()

    return {
        "mensagem": "Lançamento atualizado!",
        "lucro_liquido": lucro,
        "valor_comissao": comissao
    }

@router.delete("/lancamentos/{lancamento_id}")
def excluir_lancamento(lancamento_id: int, db: Session = Depends(get_db)):
    lanc = db.query(LancamentoInvestidor).filter(LancamentoInvestidor.id == lancamento_id).first()
    if not lanc:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")
    db.delete(lanc)
    db.commit()
    return {"mensagem": "Lançamento excluído!"}

@router.get("/{investidor_id}/extrato")
def extrato_investidor(investidor_id: int, db: Session = Depends(get_db)):
    inv = db.query(Investidor).filter(Investidor.id == investidor_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investidor não encontrado")

    lancamentos = db.query(LancamentoInvestidor).filter(
        LancamentoInvestidor.investidor_id == investidor_id
    ).order_by(LancamentoInvestidor.mes_referencia.desc()).all()

    return {
        "investidor": {
            "id": inv.id,
            "nome": inv.nome,
            "percentual_comissao": inv.percentual_comissao
        },
        "resumo": {
            "total_lancamentos": len(lancamentos),
            "total_lucro_gerado": sum(l.lucro_liquido for l in lancamentos),
            "total_comissao_paga": sum(l.valor_comissao for l in lancamentos)
        },
        "lancamentos": [
            {
                "id": l.id,
                "mes_referencia": l.mes_referencia,
                "veiculo_id": l.veiculo_id,
                "receita_total": l.receita_total,
                "aportes": l.aportes,
                "despesas_total": l.despesas_total,
                "parcelas_financiamento": l.parcelas_financiamento,
                "lucro_liquido": l.lucro_liquido,
                "percentual_comissao": l.percentual_comissao,
                "valor_comissao": l.valor_comissao,
                "observacao": l.observacao,
                "criado_em": str(l.criado_em)
            }
            for l in lancamentos
        ]
    }
