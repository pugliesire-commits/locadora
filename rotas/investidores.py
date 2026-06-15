from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from modelos.database import get_db
from modelos.investidor import Investidor
from modelos.lancamento import LancamentoInvestidor
from modelos.veiculo import Veiculo
from pydantic import BaseModel
from typing import Optional
from datetime import date

router = APIRouter(prefix="/investidores", tags=["Investidores"])

# ---------- Schemas (moldes dos dados) ----------

class InvestidorBase(BaseModel):
    nome: str
    cpf_cnpj: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None
    percentual_comissao: float  # Ex: 30.0 para 30%

class InvestidorCreate(InvestidorBase):
    pass

class LancamentoCreate(BaseModel):
    investidor_id: int
    veiculo_id: int
    mes_referencia: str          # Ex: "2025-06"
    receita_total: float
    aportes: float = 0.0
    despesas_total: float
    parcelas_financiamento: float = 0.0
    observacao: Optional[str] = None

# ---------- Rotas de Investidores ----------

@router.get("/")
def listar_investidores(db: Session = Depends(get_db)):
    """Lista todos os investidores cadastrados"""
    investidores = db.query(Investidor).all()
    resultado = []
    for inv in investidores:
        # Conta quantos carros esse investidor tem
        total_veiculos = db.query(Veiculo).filter(
            Veiculo.investidor_id == inv.id
        ).count()
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
    """Cadastra um novo investidor"""
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
    """Busca um investidor pelo ID"""
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
        "veiculos": [
            {"id": v.id, "modelo": v.modelo, "placa": v.placa, "status": v.status}
            for v in veiculos
        ]
    }

@router.put("/{investidor_id}")
def atualizar_investidor(investidor_id: int, dados: InvestidorCreate, db: Session = Depends(get_db)):
    """Atualiza os dados de um investidor"""
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
    """Desativa um investidor (não apaga do banco)"""
    inv = db.query(Investidor).filter(Investidor.id == investidor_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investidor não encontrado")
    inv.ativo = False
    db.commit()
    return {"mensagem": "Investidor desativado com sucesso!"}

# ---------- Rotas de Lançamentos ----------

@router.post("/lancamentos/novo")
def criar_lancamento(dados: LancamentoCreate, db: Session = Depends(get_db)):
    """Registra um lançamento mensal e calcula a comissão automaticamente"""
    # Busca o investidor para pegar o percentual de comissão dele
    inv = db.query(Investidor).filter(Investidor.id == dados.investidor_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investidor não encontrado")

    # Fórmula: Receita + Aportes - Despesas - Parcelas = Lucro Líquido
    lucro = dados.receita_total + dados.aportes - dados.despesas_total - dados.parcelas_financiamento

    # Se lucro negativo, comissão é zero
    if lucro > 0:
        comissao = lucro * (inv.percentual_comissao / 100)
    else:
        comissao = 0.0

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
        "mensagem": "Lançamento registrado com sucesso!",
        "id": novo.id,
        "lucro_liquido": lucro,
        "percentual_comissao": inv.percentual_comissao,
        "valor_comissao": comissao
    }

@router.get("/{investidor_id}/extrato")
def extrato_investidor(investidor_id: int, db: Session = Depends(get_db)):
    """Retorna o extrato completo de um investidor com todos os lançamentos"""
    inv = db.query(Investidor).filter(Investidor.id == investidor_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investidor não encontrado")

    lancamentos = db.query(LancamentoInvestidor).filter(
        LancamentoInvestidor.investidor_id == investidor_id
    ).order_by(LancamentoInvestidor.mes_referencia.desc()).all()

    total_comissao = sum(l.valor_comissao for l in lancamentos)
    total_lucro = sum(l.lucro_liquido for l in lancamentos)

    return {
        "investidor": {
            "id": inv.id,
            "nome": inv.nome,
            "percentual_comissao": inv.percentual_comissao
        },
        "resumo": {
            "total_lancamentos": len(lancamentos),
            "total_lucro_gerado": total_lucro,
            "total_comissao_paga": total_comissao
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

@router.get("/{investidor_id}/extrato/{mes}")
def extrato_mes(investidor_id: int, mes: str, db: Session = Depends(get_db)):
    """Retorna o extrato de um mês específico. Ex: /extrato/2025-06"""
    inv = db.query(Investidor).filter(Investidor.id == investidor_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investidor não encontrado")

    lancamentos = db.query(LancamentoInvestidor).filter(
        LancamentoInvestidor.investidor_id == investidor_id,
        LancamentoInvestidor.mes_referencia == mes
    ).all()

    return {
        "investidor": inv.nome,
        "mes": mes,
        "lancamentos": [
            {
                "id": l.id,
                "veiculo_id": l.veiculo_id,
                "receita_total": l.receita_total,
                "despesas_total": l.despesas_total,
                "lucro_liquido": l.lucro_liquido,
                "valor_comissao": l.valor_comissao
            }
            for l in lancamentos
        ],
        "total_comissao_mes": sum(l.valor_comissao for l in lancamentos)
    }
