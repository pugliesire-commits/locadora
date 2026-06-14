from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from modelos.database import get_db
from modelos.cliente import Cliente

router = APIRouter(prefix="/clientes", tags=["Clientes"])

class ClienteSchema(BaseModel):
    nome: str
    cpf: str
    rg: Optional[str] = None
    cnh: str
    cnh_cat: Optional[str] = None
    telefone: str
    email: Optional[str] = None
    endereco: Optional[str] = None

@router.get("/")
def listar_clientes(db: Session = Depends(get_db)):
    return db.query(Cliente).all()

@router.post("/")
def cadastrar_cliente(cliente: ClienteSchema, db: Session = Depends(get_db)):
    db_cliente = Cliente(**cliente.model_dump())
    db.add(db_cliente)
    db.commit()
    db.refresh(db_cliente)
    return db_cliente

@router.get("/{id}")
def buscar_cliente(id: int, db: Session = Depends(get_db)):
    cliente = db.query(Cliente).filter(Cliente.id == id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return cliente

@router.put("/{id}")
def atualizar_cliente(id: int, dados: ClienteSchema, db: Session = Depends(get_db)):
    cliente = db.query(Cliente).filter(Cliente.id == id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    for campo, valor in dados.model_dump().items():
        setattr(cliente, campo, valor)
    db.commit()
    db.refresh(cliente)
    return cliente

@router.delete("/{id}")
def excluir_cliente(id: int, db: Session = Depends(get_db)):
    cliente = db.query(Cliente).filter(Cliente.id == id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    db.delete(cliente)
    db.commit()
    return {"mensagem": "Cliente excluído com sucesso"}