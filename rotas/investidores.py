from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from modelos.database import get_db
from modelos.investidor import Investidor
from modelos.lancamento import LancamentoInvestidor
from modelos.veiculo import Veiculo
from modelos.locacao import Locacao
from modelos.parcela import Parcela
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

@router.delete("/{investidor_id}/excluir")
def excluir_investidor_permanente(investidor_id: int, db: Session = Depends(get_db)):
    inv = db.query(Investidor).filter(Investidor.id == investidor_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investidor não encontrado")
    db.query(LancamentoInvestidor).filter(LancamentoInvestidor.investidor_id == investidor_id).delete()
    db.query(Veiculo).filter(Veiculo.investidor_id == investidor_id).update({"investidor_id": None})
    db.delete(inv)
    db.commit()
    return {"mensagem": "Investidor excluido permanentemente!"}

# ---------- Extrato Automatico por mes ----------

@router.get("/{investidor_id}/extrato-automatico")
def extrato_automatico(investidor_id: int, mes: Optional[str] = None, db: Session = Depends(get_db)):
    inv = db.query(Investidor).filter(Investidor.id == investidor_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investidor não encontrado")

    veiculos = db.query(Veiculo).filter(Veiculo.investidor_id == investidor_id).all()
    if not veiculos:
        return {"investidor": {"id": inv.id, "nome": inv.nome, "percentual_comissao": inv.percentual_comissao}, "meses": [], "resumo": {"total_receita": 0, "total_despesas": 0, "total_financiamento": 0, "total_lucro": 0, "total_comissao": 0}}

    veiculo_ids = [v.id for v in veiculos]
    veiculo_map = {v.id: f"{v.placa} {v.marca} {v.modelo}" for v in veiculos}

    # Busca todas as parcelas pagas dos veiculos do investidor
    locacoes = db.query(Locacao).filter(Locacao.veiculo_id.in_(veiculo_ids)).all()
    locacao_map = {l.id: l.veiculo_id for l in locacoes}
    locacao_ids = [l.id for l in locacoes]

    parcelas_pagas = []
    if locacao_ids:
        parcelas_pagas = db.query(Parcela).filter(
            Parcela.locacao_id.in_(locacao_ids),
            Parcela.status == 'pago'
        ).all()

    # Busca despesas dos veiculos do investidor
    despesas = db.query(Despesa).filter(Despesa.veiculo_id.in_(veiculo_ids)).all()

    # Busca financiamentos dos veiculos do investidor
    financiamentos = db.query(Financiamento).filter(Financiamento.veiculo_id.in_(veiculo_ids)).all()
    fin_map = {f.veiculo_id: f for f in financiamentos}

    # Agrupa por mes
    meses = {}

    for p in parcelas_pagas:
        if not p.data_pagamento:
            continue
        mes_key = str(p.data_pagamento)[:7]
        if mes and mes_key != mes:
            continue
        veiculo_id = locacao_map.get(p.locacao_id)
        if not veiculo_id:
            continue
        chave = f"{mes_key}|{veiculo_id}"
        if chave not in meses:
            meses[chave] = {"mes": mes_key, "veiculo_id": veiculo_id, "veiculo_nome": veiculo_map.get(veiculo_id, str(veiculo_id)), "receita": 0.0, "despesas": 0.0, "financiamento": 0.0}
        meses[chave]["receita"] += p.valor_pago or 0

    for d in despesas:
        if not d.data:
            continue
        mes_key = str(d.data)[:7]
        if mes and mes_key != mes:
            continue
        chave = f"{mes_key}|{d.veiculo_id}"
        if chave not in meses:
            meses[chave] = {"mes": mes_key, "veiculo_id": d.veiculo_id, "veiculo_nome": veiculo_map.get(d.veiculo_id, str(d.veiculo_id)), "receita": 0.0, "despesas": 0.0, "financiamento": 0.0}
        meses[chave]["despesas"] += d.valor or 0

    # Adiciona parcela de financiamento por mes (valor fixo mensal)
    for chave, dados in meses.items():
        veiculo_id = dados["veiculo_id"]
        fin = fin_map.get(veiculo_id)
        if fin and not fin.quitado:
            dados["financiamento"] = fin.parcela_mensal or 0.0

    # Calcula lucro e comissao
    resultado = []
    for dados in sorted(meses.values(), key=lambda x: x["mes"], reverse=True):
        lucro = dados["receita"] - dados["despesas"] - dados["financiamento"]
        comissao = lucro * (inv.percentual_comissao / 100) if lucro > 0 else 0.0
        resultado.append({
            "mes": dados["mes"],
            "veiculo_id": dados["veiculo_id"],
            "veiculo_nome": dados["veiculo_nome"],
            "receita": round(dados["receita"], 2),
            "despesas": round(dados["despesas"], 2),
            "financiamento": round(dados["financiamento"], 2),
            "lucro_liquido": round(lucro, 2),
            "comissao": round(comissao, 2)
        })

    resumo = {
        "total_receita": round(sum(r["receita"] for r in resultado), 2),
        "total_despesas": round(sum(r["despesas"] for r in resultado), 2),
        "total_financiamento": round(sum(r["financiamento"] for r in resultado), 2),
        "total_lucro": round(sum(r["lucro_liquido"] for r in resultado), 2),
        "total_comissao": round(sum(r["comissao"] for r in resultado), 2)
    }

    return {
        "investidor": {"id": inv.id, "nome": inv.nome, "percentual_comissao": inv.percentual_comissao},
        "meses": resultado,
        "resumo": resumo
    }

# ---------- Pre-calculo automatico ----------

@router.get("/precalculo/{veiculo_id}/{mes_referencia}")
def precalculo_lancamento(veiculo_id: int, mes_referencia: str, db: Session = Depends(get_db)):
    try:
        ano, mes = int(mes_referencia.split("-")[0]), int(mes_referencia.split("-")[1])
    except:
        raise HTTPException(status_code=400, detail="Formato invalido. Use YYYY-MM")

    locacoes = db.query(Locacao).filter(Locacao.veiculo_id == veiculo_id).all()
    locacao_ids = [l.id for l in locacoes]

    receita = 0.0
    if locacao_ids:
        parcelas = db.query(Parcela).filter(
            Parcela.locacao_id.in_(locacao_ids),
            Parcela.status == 'pago',
            extract('year', Parcela.data_pagamento) == ano,
            extract('month', Parcela.data_pagamento) == mes
        ).all()
        receita = sum(p.valor_pago or 0 for p in parcelas)

    despesas = db.query(Despesa).filter(
        Despesa.veiculo_id == veiculo_id,
        extract('year', Despesa.data) == ano,
        extract('month', Despesa.data) == mes
    ).all()
    total_despesas = sum(d.valor or 0 for d in despesas)

    financiamento = db.query(Financiamento).filter(
        Financiamento.veiculo_id == veiculo_id
    ).first()
    parcela = financiamento.parcela_mensal if financiamento and not financiamento.quitado else 0.0

    return {
        "veiculo_id": veiculo_id,
        "mes_referencia": mes_referencia,
        "receita_total": round(receita, 2),
        "despesas_total": round(total_despesas, 2),
        "parcelas_financiamento": round(parcela, 2),
        "total_locacoes": len(locacoes),
        "total_despesas_registradas": len(despesas)
    }

# ---------- Lancamentos ----------

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
    return {"mensagem": "Lancamento registrado!", "id": novo.id, "lucro_liquido": lucro, "valor_comissao": comissao}

@router.put("/lancamentos/{lancamento_id}")
def editar_lancamento(lancamento_id: int, dados: LancamentoUpdate, db: Session = Depends(get_db)):
    lanc = db.query(LancamentoInvestidor).filter(LancamentoInvestidor.id == lancamento_id).first()
    if not lanc:
        raise HTTPException(status_code=404, detail="Lancamento não encontrado")
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
    return {"mensagem": "Lancamento atualizado!", "lucro_liquido": lucro, "valor_comissao": comissao}

@router.delete("/lancamentos/{lancamento_id}")
def excluir_lancamento(lancamento_id: int, db: Session = Depends(get_db)):
    lanc = db.query(LancamentoInvestidor).filter(LancamentoInvestidor.id == lancamento_id).first()
    if not lanc:
        raise HTTPException(status_code=404, detail="Lancamento não encontrado")
    db.delete(lanc)
    db.commit()
    return {"mensagem": "Lancamento excluido!"}

# ---------- Extrato detalhado (manual) ----------

@router.get("/{investidor_id}/extrato")
def extrato_investidor(investidor_id: int, db: Session = Depends(get_db)):
    inv = db.query(Investidor).filter(Investidor.id == investidor_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investidor não encontrado")
    lancamentos = db.query(LancamentoInvestidor).filter(
        LancamentoInvestidor.investidor_id == investidor_id
    ).order_by(LancamentoInvestidor.mes_referencia.desc()).all()
    return {
        "investidor": {"id": inv.id, "nome": inv.nome, "percentual_comissao": inv.percentual_comissao},
        "resumo": {
            "total_lancamentos": len(lancamentos),
            "total_lucro_gerado": sum(l.lucro_liquido for l in lancamentos),
            "total_comissao_paga": sum(l.valor_comissao for l in lancamentos)
        },
        "lancamentos": [{"id": l.id, "mes_referencia": l.mes_referencia, "veiculo_id": l.veiculo_id, "receita_total": l.receita_total, "aportes": l.aportes, "despesas_total": l.despesas_total, "parcelas_financiamento": l.parcelas_financiamento, "lucro_liquido": l.lucro_liquido, "percentual_comissao": l.percentual_comissao, "valor_comissao": l.valor_comissao, "observacao": l.observacao, "criado_em": str(l.criado_em)} for l in lancamentos]
    }

# ---------- Extrato CONSOLIDADO por mes (manual) ----------

@router.get("/{investidor_id}/extrato-consolidado")
def extrato_consolidado(investidor_id: int, db: Session = Depends(get_db)):
    inv = db.query(Investidor).filter(Investidor.id == investidor_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investidor não encontrado")
    lancamentos = db.query(LancamentoInvestidor).filter(
        LancamentoInvestidor.investidor_id == investidor_id
    ).order_by(LancamentoInvestidor.mes_referencia.desc()).all()
    grupos = {}
    for l in lancamentos:
        chave = f"{l.mes_referencia}|{l.veiculo_id}"
        if chave not in grupos:
            grupos[chave] = {"mes_referencia": l.mes_referencia, "veiculo_id": l.veiculo_id, "receita_total": 0.0, "aportes": 0.0, "despesas_total": 0.0, "parcelas_financiamento": 0.0, "lucro_liquido": 0.0, "valor_comissao": 0.0, "percentual_comissao": l.percentual_comissao, "total_lancamentos": 0, "lancamentos_detalhes": []}
        g = grupos[chave]
        g["receita_total"] += l.receita_total
        g["aportes"] += l.aportes
        g["despesas_total"] += l.despesas_total
        g["parcelas_financiamento"] += l.parcelas_financiamento
        g["total_lancamentos"] += 1
        g["lancamentos_detalhes"].append({"id": l.id, "receita_total": l.receita_total, "aportes": l.aportes, "despesas_total": l.despesas_total, "parcelas_financiamento": l.parcelas_financiamento, "lucro_liquido": l.lucro_liquido, "valor_comissao": l.valor_comissao, "observacao": l.observacao})
    consolidados = []
    for g in grupos.values():
        lucro = g["receita_total"] + g["aportes"] - g["despesas_total"] - g["parcelas_financiamento"]
        comissao = lucro * (inv.percentual_comissao / 100) if lucro > 0 else 0.0
        g["lucro_liquido"] = round(lucro, 2)
        g["valor_comissao"] = round(comissao, 2)
        g["receita_total"] = round(g["receita_total"], 2)
        g["aportes"] = round(g["aportes"], 2)
        g["despesas_total"] = round(g["despesas_total"], 2)
        g["parcelas_financiamento"] = round(g["parcelas_financiamento"], 2)
        consolidados.append(g)
    total_lucro = sum(g["lucro_liquido"] for g in consolidados)
    total_comissao = sum(g["valor_comissao"] for g in consolidados)
    return {
        "investidor": {"id": inv.id, "nome": inv.nome, "percentual_comissao": inv.percentual_comissao},
        "resumo": {"total_meses": len(consolidados), "total_lucro_gerado": round(total_lucro, 2), "total_comissao_paga": round(total_comissao, 2)},
        "consolidado": consolidados
    }
