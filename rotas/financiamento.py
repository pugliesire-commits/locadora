from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from modelos.database import get_db
from modelos.financiamento import Financiamento
from modelos.veiculo import Veiculo
from modelos.locacao import Locacao
from modelos.despesa import Despesa
from modelos.seguranca import verificar_token
from pydantic import BaseModel
from datetime import date, timedelta
from typing import Optional

router = APIRouter(prefix="/financiamentos", tags=["Financiamentos"])

class FinanciamentoCreate(BaseModel):
    veiculo_id: int
    banco: str
    valor_financiado: float
    entrada: float = 0.0
    parcela_mensal: float
    total_parcelas: int
    parcelas_pagas: int = 0
    data_inicio: date

class FinanciamentoUpdate(BaseModel):
    banco: Optional[str] = None
    valor_financiado: Optional[float] = None
    entrada: Optional[float] = None
    parcela_mensal: Optional[float] = None
    total_parcelas: Optional[int] = None
    parcelas_pagas: Optional[int] = None
    data_inicio: Optional[date] = None

@router.post("/")
def criar_financiamento(dados: FinanciamentoCreate, db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    veiculo = db.query(Veiculo).filter(Veiculo.id == dados.veiculo_id).first()
    if not veiculo:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")
    financiamento = Financiamento(**dados.dict())
    db.add(financiamento)
    db.flush()
    # Se houver entrada, registra como despesa vinculada ao veículo
    if dados.entrada and dados.entrada > 0:
        despesa_entrada = Despesa(
            categoria="outros",
            descricao=f"Entrada financiamento {dados.banco} — {veiculo.placa}",
            valor=dados.entrada,
            data=dados.data_inicio,
            veiculo_id=dados.veiculo_id
        )
        db.add(despesa_entrada)
    db.commit()
    db.refresh(financiamento)
    return {"mensagem": "Financiamento criado com sucesso", "id": financiamento.id}

@router.get("/")
def listar_financiamentos(db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    financiamentos = db.query(Financiamento).all()
    resultado = []
    for f in financiamentos:
        from dateutil.relativedelta import relativedelta
        proxima = f.data_inicio + relativedelta(months=f.parcelas_pagas)
        resultado.append({
            "id": f.id,
            "veiculo_id": f.veiculo_id,
            "placa": f.veiculo.placa if f.veiculo else None,
            "modelo": f.veiculo.modelo if f.veiculo else None,
            "banco": f.banco,
            "valor_financiado": f.valor_financiado,
            "entrada": f.entrada,
            "parcela_mensal": f.parcela_mensal,
            "total_parcelas": f.total_parcelas,
            "parcelas_pagas": f.parcelas_pagas,
            "parcelas_restantes": f.parcelas_restantes,
            "total_pago": f.total_pago,
            "total_devido": f.total_devido,
            "quitado": f.quitado,
            "data_inicio": f.data_inicio,
            "proxima_parcela": proxima.isoformat(),
            "investidor_id": f.veiculo.investidor_id if f.veiculo else None
        })
    return resultado
@router.get("/alertas")
def alertas_vencimento(db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    hoje = date.today()
    alertas = []
    financiamentos = db.query(Financiamento).filter(
        Financiamento.parcelas_pagas < Financiamento.total_parcelas
    ).all()
    for f in financiamentos:
        from dateutil.relativedelta import relativedelta
        proxima = f.data_inicio + relativedelta(months=f.parcelas_pagas)
        dias_restantes = (proxima - hoje).days
        if dias_restantes <= 30:
            alertas.append({
                "id": f.id,
                "veiculo_id": f.veiculo_id,
                "placa": f.veiculo.placa if f.veiculo else None,
                "banco": f.banco,
                "parcela_mensal": f.parcela_mensal,
                "proxima_parcela": proxima.isoformat(),
                "dias_restantes": dias_restantes,
                "vencido": dias_restantes < 0
            })
    alertas.sort(key=lambda x: x["dias_restantes"])
    return alertas

@router.get("/relatorio")
def relatorio_receita_vs_parcela(db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    financiamentos = db.query(Financiamento).all()
    relatorio = []
    for f in financiamentos:
        receita = db.query(func.sum(Locacao.valor_total)).filter(
            Locacao.veiculo_id == f.veiculo_id
        ).scalar() or 0
        relatorio.append({
            "veiculo_id": f.veiculo_id,
            "placa": f.veiculo.placa if f.veiculo else None,
            "modelo": f.veiculo.modelo if f.veiculo else None,
            "banco": f.banco,
            "total_pago_parcelas": f.total_pago,
            "receita_gerada": receita,
            "saldo": receita - f.total_pago,
            "situacao": "✅ Lucrativo" if receita >= f.total_pago else "⚠️ Prejuízo"
        })
    return relatorio

@router.get("/dashboard")
def dashboard_financiamentos(db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    todos = db.query(Financiamento).all()
    total_parcela_mes = sum(f.parcela_mensal for f in todos if not f.quitado)
    quitados = sum(1 for f in todos if f.quitado)
    ativos = sum(1 for f in todos if not f.quitado)
    return {
        "total_financiamentos": len(todos),
        "financiamentos_ativos": ativos,
        "financiamentos_quitados": quitados,
        "total_parcelas_mes": total_parcela_mes
    }

@router.put("/{financiamento_id}/pagar-parcela")
def pagar_parcela(financiamento_id: int, db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    f = db.query(Financiamento).filter(Financiamento.id == financiamento_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Financiamento não encontrado")
    if f.quitado:
        raise HTTPException(status_code=400, detail="Financiamento já quitado")
    f.parcelas_pagas += 1
    db.commit()
    return {
        "mensagem": "Parcela registrada!",
        "parcelas_pagas": f.parcelas_pagas,
        "parcelas_restantes": f.parcelas_restantes
    }

@router.put("/{financiamento_id}")
def editar_financiamento(financiamento_id: int, dados: FinanciamentoUpdate, db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    f = db.query(Financiamento).filter(Financiamento.id == financiamento_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Financiamento não encontrado")
    for campo, valor in dados.dict(exclude_unset=True).items():
        setattr(f, campo, valor)
    db.commit()
    db.refresh(f)
    return {"mensagem": "Financiamento atualizado!", "id": f.id}

@router.delete("/{financiamento_id}")
def deletar_financiamento(financiamento_id: int, db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    f = db.query(Financiamento).filter(Financiamento.id == financiamento_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Financiamento não encontrado")
    db.delete(f)
    db.commit()
    return {"mensagem": "Financiamento removido com sucesso"}
