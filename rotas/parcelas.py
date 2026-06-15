from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from modelos.database import get_db
from modelos.parcela import Parcela
from modelos.locacao import Locacao

router = APIRouter(prefix="/parcelas", tags=["Parcelas"])

class PagamentoParcela(BaseModel):
    forma_pagamento: str
    valor_pago: float
    observacao: Optional[str] = None

@router.get("/locacao/{locacao_id}")
def listar_parcelas(locacao_id: int, db: Session = Depends(get_db)):
    parcelas = db.query(Parcela).filter(
        Parcela.locacao_id == locacao_id
    ).order_by(Parcela.numero).all()
    return parcelas

@router.get("/locacao/{locacao_id}/resumo")
def resumo_parcelas(locacao_id: int, db: Session = Depends(get_db)):
    parcelas = db.query(Parcela).filter(Parcela.locacao_id == locacao_id).all()
    total = sum(p.valor for p in parcelas)
    pago = sum(p.valor_pago for p in parcelas)
    pendente = total - pago
    pagas = len([p for p in parcelas if p.status == 'pago'])
    pendentes = len([p for p in parcelas if p.status == 'pendente'])
    parciais = len([p for p in parcelas if p.status == 'parcial'])
    return {
        "total_parcelas": len(parcelas),
        "valor_total": total,
        "valor_pago": pago,
        "valor_pendente": pendente,
        "pagas": pagas,
        "pendentes": pendentes,
        "parciais": parciais
    }

@router.put("/{parcela_id}/pagar")
def pagar_parcela(parcela_id: int, dados: PagamentoParcela, db: Session = Depends(get_db)):
    parcela = db.query(Parcela).filter(Parcela.id == parcela_id).first()
    if not parcela:
        raise HTTPException(status_code=404, detail="Parcela não encontrada")
    if parcela.status == 'pago':
        raise HTTPException(status_code=400, detail="Parcela já está paga")

    parcela.valor_pago = (parcela.valor_pago or 0) + dados.valor_pago
    parcela.forma_pagamento = dados.forma_pagamento
    parcela.observacao = dados.observacao
    parcela.data_pagamento = date.today()

    if parcela.valor_pago >= parcela.valor:
        parcela.status = 'pago'
    else:
        parcela.status = 'parcial'

    db.commit()
    db.refresh(parcela)
    return parcela

@router.delete("/locacao/{locacao_id}")
def excluir_parcelas_locacao(locacao_id: int, db: Session = Depends(get_db)):
    db.query(Parcela).filter(Parcela.locacao_id == locacao_id).delete()
    db.commit()
    return {"mensagem": "Parcelas excluídas"}
