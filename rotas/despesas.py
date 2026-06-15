from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from modelos.database import get_db
from modelos.despesa import Despesa
from modelos.veiculo import Veiculo
from modelos.financiamento import Financiamento
from modelos.seguranca import verificar_token
from pydantic import BaseModel
from datetime import date
from typing import Optional

router = APIRouter(prefix="/despesas", tags=["Despesas"])

CATEGORIAS = [
    "manutencao", "combustivel", "lavagem", "salarios",
    "contas", "aluguel", "seguro", "ipva_licenciamento",
    "pecas", "outros"
]

class DespesaCreate(BaseModel):
    categoria: str
    descricao: str
    valor: float
    data: date
    veiculo_id: Optional[int] = None

@router.post("/")
def criar_despesa(dados: DespesaCreate, db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    if dados.veiculo_id:
        veiculo = db.query(Veiculo).filter(Veiculo.id == dados.veiculo_id).first()
        if not veiculo:
            raise HTTPException(status_code=404, detail="Veículo não encontrado")
    despesa = Despesa(**dados.dict())
    db.add(despesa)
    db.commit()
    db.refresh(despesa)
    return {"mensagem": "Despesa registrada com sucesso", "id": despesa.id}

@router.get("/")
def listar_despesas(db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    despesas = db.query(Despesa).order_by(Despesa.data.desc()).all()
    resultado = []
    for d in despesas:
        resultado.append({
            "id": d.id,
            "categoria": d.categoria,
            "descricao": d.descricao,
            "valor": d.valor,
            "data": d.data,
            "veiculo_id": d.veiculo_id,
            "placa": d.veiculo.placa if d.veiculo else None,
            "modelo": d.veiculo.modelo if d.veiculo else None
        })
    return resultado

@router.get("/dashboard")
def dashboard_despesas(db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    from datetime import datetime
    mes_atual = datetime.now().month
    ano_atual = datetime.now().year
    todas = db.query(Despesa).all()
    do_mes = [d for d in todas if d.data.month == mes_atual and d.data.year == ano_atual]
    total_geral = sum(d.valor for d in todas)
    total_mes = sum(d.valor for d in do_mes)
    return {
        "total_despesas_geral": total_geral,
        "total_despesas_mes": total_mes,
        "quantidade_mes": len(do_mes),
        "quantidade_geral": len(todas)
    }

@router.get("/por-categoria")
def relatorio_por_categoria(db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    despesas = db.query(Despesa).all()
    categorias = {}
    for d in despesas:
        if d.categoria not in categorias:
            categorias[d.categoria] = {"total": 0, "quantidade": 0}
        categorias[d.categoria]["total"] += d.valor
        categorias[d.categoria]["quantidade"] += 1
    return [{"categoria": k, "total": v["total"], "quantidade": v["quantidade"]}
            for k, v in sorted(categorias.items(), key=lambda x: x[1]["total"], reverse=True)]

@router.get("/por-veiculo")
def relatorio_por_veiculo(db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    veiculos = db.query(Veiculo).all()
    resultado = []
    for v in veiculos:
        despesas = db.query(Despesa).filter(Despesa.veiculo_id == v.id).all()
        total_despesas = sum(d.valor for d in despesas)
        financiamentos = db.query(Financiamento).filter(Financiamento.veiculo_id == v.id).all()
        total_parcelas = sum(f.total_pago for f in financiamentos)
        custo_total = total_despesas + total_parcelas
        resultado.append({
            "veiculo_id": v.id,
            "placa": v.placa,
            "modelo": v.modelo,
            "marca": v.marca,
            "total_despesas": total_despesas,
            "total_parcelas_financiamento": total_parcelas,
            "custo_total": custo_total
        })
    return sorted(resultado, key=lambda x: x["custo_total"], reverse=True)

@router.delete("/{despesa_id}")
def deletar_despesa(despesa_id: int, db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    d = db.query(Despesa).filter(Despesa.id == despesa_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Despesa não encontrada")
    db.delete(d)
    db.commit()
    return {"mensagem": "Despesa removida com sucesso"}
