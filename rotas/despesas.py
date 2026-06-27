from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from modelos.database import get_db
from modelos.despesa import Despesa
from modelos.veiculo import Veiculo
from modelos.financiamento import Financiamento
from modelos.seguranca import verificar_token
from pydantic import BaseModel
from datetime import date
from dateutil.relativedelta import relativedelta
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
    parcelas: Optional[int] = 1

@router.post("/")
def criar_despesa(dados: DespesaCreate, db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    if dados.veiculo_id:
        veiculo = db.query(Veiculo).filter(Veiculo.id == dados.veiculo_id).first()
        if not veiculo:
            raise HTTPException(status_code=404, detail="Veiculo nao encontrado")
    parcelas = dados.parcelas or 1
    valor_parcela = round(dados.valor / parcelas, 2)
    ids = []
    for i in range(parcelas):
        data_parcela = dados.data + relativedelta(months=i)
        descricao = dados.descricao
        if parcelas > 1:
            descricao = f"{dados.descricao} ({i+1}/{parcelas})"
        despesa = Despesa(
            categoria=dados.categoria,
            descricao=descricao,
            valor=valor_parcela,
            data=data_parcela,
            veiculo_id=dados.veiculo_id
        )
        db.add(despesa)
        db.flush()
        ids.append(despesa.id)
    db.commit()
    return {"mensagem": f"Despesa registrada em {parcelas} parcela(s)", "ids": ids}

@router.get("/")
def listar_despesas(mes: Optional[str] = Query(None), db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    query = db.query(Despesa)
    if mes:
        ano, m = mes.split("-")
        query = query.filter(
            func.extract('year', Despesa.data) == int(ano),
            func.extract('month', Despesa.data) == int(m)
        )
    despesas = query.order_by(Despesa.data.desc()).all()
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
def relatorio_por_veiculo(mes: Optional[str] = Query(None), db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    veiculos = db.query(Veiculo).all()
    resultado = []
    ano_filtro, mes_filtro = None, None
    if mes:
        ano_filtro, mes_filtro = int(mes.split("-")[0]), int(mes.split("-")[1])
    for v in veiculos:
        query_desp = db.query(Despesa).filter(Despesa.veiculo_id == v.id)
        if ano_filtro and mes_filtro:
            query_desp = query_desp.filter(
                func.extract('year', Despesa.data) == ano_filtro,
                func.extract('month', Despesa.data) == mes_filtro
            )
        total_despesas = sum(d.valor for d in query_desp.all())
        financiamentos = db.query(Financiamento).filter(Financiamento.veiculo_id == v.id).all()
        total_parcelas = 0
        if ano_filtro and mes_filtro:
            from datetime import date as date_type
            inicio = date_type(ano_filtro, mes_filtro, 1)
            for f in financiamentos:
                meses_desde = (ano_filtro - f.data_inicio.year) * 12 + (mes_filtro - f.data_inicio.month)
                if 0 <= meses_desde < f.parcelas_pagas:
                    total_parcelas += f.parcela_mensal
        else:
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
        raise HTTPException(status_code=404, detail="Despesa nao encontrada")
    db.delete(d)
    db.commit()
    return {"mensagem": "Despesa removida com sucesso"}
