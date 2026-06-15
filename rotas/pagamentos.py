from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from modelos.database import get_db
from modelos.pagamento import Pagamento, CobrancaExtra, FormaPagamento, StatusPagamento
from modelos.locacao import Locacao
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/pagamentos", tags=["Pagamentos"])

class PagamentoCreate(BaseModel):
    locacao_id: int
    valor_pago: float
    forma_pagamento: FormaPagamento
    observacao: Optional[str] = None

class CobrancaExtraCreate(BaseModel):
    locacao_id: int
    tipo: str
    descricao: Optional[str] = None
    valor: float

# Registrar pagamento
@router.post("/")
def registrar_pagamento(dados: PagamentoCreate, db: Session = Depends(get_db)):
    locacao = db.query(Locacao).filter(Locacao.id == dados.locacao_id).first()
    if not locacao:
        raise HTTPException(status_code=404, detail="Locação não encontrada")

    pagamento_existente = db.query(Pagamento).filter(
        Pagamento.locacao_id == dados.locacao_id
    ).first()

    if pagamento_existente:
        pagamento_existente.valor_pago += dados.valor_pago
        pagamento_existente.valor_pendente = max(
            0, pagamento_existente.valor_total - pagamento_existente.valor_pago
        )
        if pagamento_existente.valor_pago >= pagamento_existente.valor_total:
            pagamento_existente.status = StatusPagamento.pago
            locacao.status = "Paga"
        else:
            pagamento_existente.status = StatusPagamento.parcial
        pagamento_existente.forma_pagamento = dados.forma_pagamento
        pagamento_existente.observacao = dados.observacao
        db.commit()
        db.refresh(pagamento_existente)
        return pagamento_existente

    valor_pendente = locacao.valor_total - dados.valor_pago
    status = StatusPagamento.pago if valor_pendente <= 0 else (
        StatusPagamento.parcial if dados.valor_pago > 0 else StatusPagamento.pendente
    )
    if status == StatusPagamento.pago:
        locacao.status = "Paga"

    novo = Pagamento(
        locacao_id=dados.locacao_id,
        valor_total=locacao.valor_total,
        valor_pago=dados.valor_pago,
        valor_pendente=max(0, valor_pendente),
        forma_pagamento=dados.forma_pagamento,
        status=status,
        observacao=dados.observacao
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo

# Buscar pagamento de uma locação
@router.get("/locacao/{locacao_id}")
def buscar_pagamento(locacao_id: int, db: Session = Depends(get_db)):
    pagamento = db.query(Pagamento).filter(
        Pagamento.locacao_id == locacao_id
    ).first()
    if not pagamento:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    return pagamento

# Listar todos os pagamentos
@router.get("/")
def listar_pagamentos(db: Session = Depends(get_db)):
    return db.query(Pagamento).all()

# Listar pagamentos pendentes
@router.get("/pendentes")
def listar_pendentes(db: Session = Depends(get_db)):
    return db.query(Pagamento).filter(
        Pagamento.status != StatusPagamento.pago
    ).all()

# Adicionar cobrança extra
@router.post("/extras")
def adicionar_cobranca_extra(dados: CobrancaExtraCreate, db: Session = Depends(get_db)):
    locacao = db.query(Locacao).filter(Locacao.id == dados.locacao_id).first()
    if not locacao:
        raise HTTPException(status_code=404, detail="Locação não encontrada")
    extra = CobrancaExtra(
        locacao_id=dados.locacao_id,
        tipo=dados.tipo,
        descricao=dados.descricao,
        valor=dados.valor
    )
    db.add(extra)
    locacao.valor_total += dados.valor
    db.commit()
    db.refresh(extra)
    return extra

# Listar cobranças extras de uma locação
@router.get("/extras/{locacao_id}")
def listar_extras(locacao_id: int, db: Session = Depends(get_db)):
    return db.query(CobrancaExtra).filter(
        CobrancaExtra.locacao_id == locacao_id
    ).all()

# Resumo financeiro de uma locação
@router.get("/resumo/{locacao_id}")
def resumo_locacao(locacao_id: int, db: Session = Depends(get_db)):
    locacao = db.query(Locacao).filter(Locacao.id == locacao_id).first()
    if not locacao:
        raise HTTPException(status_code=404, detail="Locação não encontrada")
    pagamento = db.query(Pagamento).filter(
        Pagamento.locacao_id == locacao_id
    ).first()
    extras = db.query(CobrancaExtra).filter(
        CobrancaExtra.locacao_id == locacao_id
    ).all()
    total_extras = sum(e.valor for e in extras)
    return {
        "locacao_id": locacao_id,
        "valor_base": locacao.valor_total - total_extras,
        "total_extras": total_extras,
        "valor_total": locacao.valor_total,
        "valor_pago": pagamento.valor_pago if pagamento else 0,
        "valor_pendente": pagamento.valor_pendente if pagamento else locacao.valor_total,
        "status": pagamento.status if pagamento else "pendente",
        "extras": [{"tipo": e.tipo, "valor": e.valor} for e in extras]
    }