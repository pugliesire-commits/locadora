from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import extract
from modelos.database import SessionLocal
from modelos.aporte import Aporte
from pydantic import BaseModel
from datetime import date
from typing import Optional

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class AporteSchema(BaseModel):
    categoria: str
    descricao: str
    valor: float
    data: Optional[date] = None

    class Config:
        from_attributes = True

@router.get("/aportes")
def listar_aportes(mes: Optional[int] = None, ano: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Aporte)
    if mes:
        query = query.filter(extract('month', Aporte.data) == mes)
    if ano:
        query = query.filter(extract('year', Aporte.data) == ano)
    return query.order_by(Aporte.data.desc()).all()

@router.post("/aportes")
def criar_aporte(aporte: AporteSchema, db: Session = Depends(get_db)):
    novo = Aporte(
        categoria=aporte.categoria,
        descricao=aporte.descricao,
        valor=aporte.valor,
        data=aporte.data or date.today()
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo

@router.put("/aportes/{aporte_id}")
def editar_aporte(aporte_id: int, aporte: AporteSchema, db: Session = Depends(get_db)):
    registro = db.query(Aporte).filter(Aporte.id == aporte_id).first()
    if not registro:
        raise HTTPException(status_code=404, detail="Aporte não encontrado")
    registro.categoria = aporte.categoria
    registro.descricao = aporte.descricao
    registro.valor = aporte.valor
    if aporte.data:
        registro.data = aporte.data
    db.commit()
    db.refresh(registro)
    return registro

@router.delete("/aportes/{aporte_id}")
def excluir_aporte(aporte_id: int, db: Session = Depends(get_db)):
    registro = db.query(Aporte).filter(Aporte.id == aporte_id).first()
    if not registro:
        raise HTTPException(status_code=404, detail="Aporte não encontrado")
    db.delete(registro)
    db.commit()
    return {"ok": True}

@router.get("/aportes/total")
def total_aportes(mes: Optional[int] = None, ano: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Aporte)
    if mes:
        query = query.filter(extract('month', Aporte.data) == mes)
    if ano:
        query = query.filter(extract('year', Aporte.data) == ano)
    total = sum(a.valor for a in query.all())
    return {"total": total}
