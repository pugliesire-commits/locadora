from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from modelos.database import get_db
from modelos.veiculo import Veiculo

router = APIRouter(prefix="/veiculos", tags=["Veículos"])

class VeiculoSchema(BaseModel):
    placa: str
    marca: str
    modelo: str
    ano: int
    categoria: str
    cor: Optional[str] = None
    valor_diaria: float
    status: Optional[str] = "Disponível"
    investidor_id: Optional[int] = None

@router.get("/")
def listar_veiculos(db: Session = Depends(get_db)):
    return db.query(Veiculo).all()

@router.post("/")
def cadastrar_veiculo(veiculo: VeiculoSchema, db: Session = Depends(get_db)):
    db_veiculo = Veiculo(**veiculo.model_dump())
    db.add(db_veiculo)
    db.commit()
    db.refresh(db_veiculo)
    return db_veiculo

@router.get("/{id}")
def buscar_veiculo(id: int, db: Session = Depends(get_db)):
    veiculo = db.query(Veiculo).filter(Veiculo.id == id).first()
    if not veiculo:
        raise HTTPException(status_code=404, detail="Veiculo nao encontrado")
    return veiculo

@router.put("/{id}")
def atualizar_veiculo(id: int, dados: VeiculoSchema, db: Session = Depends(get_db)):
    veiculo = db.query(Veiculo).filter(Veiculo.id == id).first()
    if not veiculo:
        raise HTTPException(status_code=404, detail="Veiculo nao encontrado")
    for campo, valor in dados.model_dump().items():
        setattr(veiculo, campo, valor)
    db.commit()
    db.refresh(veiculo)
    return veiculo

@router.delete("/{id}")
def excluir_veiculo(id: int, db: Session = Depends(get_db)):
    veiculo = db.query(Veiculo).filter(Veiculo.id == id).first()
    if not veiculo:
        raise HTTPException(status_code=404, detail="Veiculo nao encontrado")
    db.delete(veiculo)
    db.commit()
    return {"mensagem": "Veiculo excluido com sucesso"}
