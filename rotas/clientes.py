from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from modelos.database import get_db
from modelos.cliente import Cliente
from modelos.locacao import Locacao

router = APIRouter(prefix="/clientes", tags=["Clientes"])

class ClienteSchema(BaseModel):
    nome: str
    cpf: Optional[str] = None
    rg: Optional[str] = None
    cnh: Optional[str] = None
    cnh_cat: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    estado_civil: Optional[str] = None
    endereco: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    cep: Optional[str] = None

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
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")
    return cliente

@router.put("/{id}")
def atualizar_cliente(id: int, dados: ClienteSchema, db: Session = Depends(get_db)):
    cliente = db.query(Cliente).filter(Cliente.id == id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")
    for campo, valor in dados.model_dump().items():
        setattr(cliente, campo, valor)
    db.commit()
    db.refresh(cliente)
    return cliente

@router.delete("/{id}")
def excluir_cliente(id: int, db: Session = Depends(get_db)):
    cliente = db.query(Cliente).filter(Cliente.id == id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")
    locacoes = db.query(Locacao).filter(Locacao.cliente_id == id).count()
    if locacoes > 0:
        raise HTTPException(status_code=400, detail=f"Cliente possui {locacoes} locacao(oes) vinculada(s). Exclua as locacoes primeiro.")
    db.delete(cliente)
    db.commit()
    return {"mensagem": "Cliente excluido com sucesso"}
