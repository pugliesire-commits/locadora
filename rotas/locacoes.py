from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from modelos.database import get_db
from modelos.locacao import Locacao
from modelos.veiculo import Veiculo

router = APIRouter(prefix="/locacoes", tags=["Locações"])

class LocacaoSchema(BaseModel):
    cliente_id: int
    veiculo_id: int
    data_inicio: str
    data_fim: str
    observacoes: Optional[str] = None

@router.get("/")
def listar_locacoes(db: Session = Depends(get_db)):
    return db.query(Locacao).all()

@router.post("/")
def criar_locacao(locacao: LocacaoSchema, db: Session = Depends(get_db)):
    veiculo = db.query(Veiculo).filter(Veiculo.id == locacao.veiculo_id).first()
    if not veiculo:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")
    if veiculo.status != "Disponível":
        raise HTTPException(status_code=400, detail="Veículo não está disponível")
    from datetime import datetime
    inicio = datetime.strptime(locacao.data_inicio, "%Y-%m-%d")
    fim = datetime.strptime(locacao.data_fim, "%Y-%m-%d")
    dias = (fim - inicio).days
    if dias <= 0:
        raise HTTPException(status_code=400, detail="Data de devolução deve ser após a retirada")
    valor_total = dias * veiculo.valor_diaria
    db_locacao = Locacao(
        cliente_id=locacao.cliente_id,
        veiculo_id=locacao.veiculo_id,
        data_inicio=locacao.data_inicio,
        data_fim=locacao.data_fim,
        dias=dias,
        valor_diaria=veiculo.valor_diaria,
        valor_total=valor_total,
        observacoes=locacao.observacoes,
        status="Ativa"
    )
    db.add(db_locacao)
    veiculo.status = "Alugado"
    db.commit()
    db.refresh(db_locacao)
    return db_locacao

@router.get("/{id}")
def buscar_locacao(id: int, db: Session = Depends(get_db)):
    locacao = db.query(Locacao).filter(Locacao.id == id).first()
    if not locacao:
        raise HTTPException(status_code=404, detail="Locação não encontrada")
    return locacao

@router.put("/{id}/devolver")
def devolver_veiculo(id: int, db: Session = Depends(get_db)):
    locacao = db.query(Locacao).filter(Locacao.id == id).first()
    if not locacao:
        raise HTTPException(status_code=404, detail="Locação não encontrada")
    if locacao.status != "Ativa":
        raise HTTPException(status_code=400, detail="Locação não está ativa")
    from datetime import datetime
    hoje = datetime.today()
    fim = datetime.strptime(locacao.data_fim, "%Y-%m-%d")
    atraso = max(0, (hoje - fim).days)
    multa = atraso * locacao.valor_diaria * 1.5
    locacao.status = "Concluída"
    valor_final = locacao.valor_total + multa
    veiculo = db.query(Veiculo).filter(Veiculo.id == locacao.veiculo_id).first()
    if veiculo:
        veiculo.status = "Disponível"
    db.commit()
    return {
        "mensagem": "Devolução registrada com sucesso",
        "dias_atraso": atraso,
        "multa": multa,
        "valor_final": valor_final
    }

@router.delete("/{id}")
def excluir_locacao(id: int, db: Session = Depends(get_db)):
    locacao = db.query(Locacao).filter(Locacao.id == id).first()
    if not locacao:
        raise HTTPException(status_code=404, detail="Locação não encontrada")
    veiculo = db.query(Veiculo).filter(Veiculo.id == locacao.veiculo_id).first()
    if veiculo:
        veiculo.status = "Disponível"
    db.delete(locacao)
    db.commit()
    return {"mensagem": "Locação excluída com sucesso"}
