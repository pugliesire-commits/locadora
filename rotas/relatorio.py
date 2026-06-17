from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from modelos.database import get_db
from modelos.locacao import Locacao
from modelos.parcela import Parcela
from modelos.financiamento import Financiamento
from modelos.despesa import Despesa
from modelos.seguranca import verificar_token
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

router = APIRouter(prefix="/relatorio", tags=["Relatório"])

@router.get("/contas-do-mes")
def contas_do_mes(mes: str = None, db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    if not mes:
        hoje = date.today()
        mes = hoje.strftime("%Y-%m")
    ano, m = int(mes.split("-")[0]), int(mes.split("-")[1])
    inicio_mes = date(ano, m, 1)
    if m == 12:
        fim_mes = date(ano + 1, 1, 1) - timedelta(days=1)
    else:
        fim_mes = date(ano, m + 1, 1) - timedelta(days=1)

    parcelas = db.query(Parcela).filter(
        Parcela.data_vencimento >= inicio_mes,
        Parcela.data_vencimento <= fim_mes
    ).all()

    a_receber = []
    for p in parcelas:
        locacao = db.query(Locacao).filter(Locacao.id == p.locacao_id).first()
        a_receber.append({
            "id": p.id,
            "tipo": "parcela_locacao",
            "descricao": f"Parcela #{p.numero} — Locação #{p.locacao_id}",
            "cliente_id": locacao.cliente_id if locacao else None,
            "vencimento": p.data_vencimento.isoformat(),
            "valor": p.valor,
            "valor_pago": p.valor_pago or 0,
            "status": p.status
        })

    a_pagar_fin = []
    financiamentos = db.query(Financiamento).filter(
        Financiamento.parcelas_pagas < Financiamento.total_parcelas
    ).all()
    for f in financiamentos:
        proxima = f.data_inicio + relativedelta(months=f.parcelas_pagas)
        if inicio_mes <= proxima <= fim_mes:
            a_pagar_fin.append({
                "id": f.id,
                "tipo": "financiamento",
                "descricao": f"Financiamento {f.banco} — {f.veiculo.placa if f.veiculo else ''}",
                "vencimento": proxima.isoformat(),
                "valor": f.parcela_mensal,
                "status": "pendente"
            })

    despesas = db.query(Despesa).filter(
        Despesa.data >= inicio_mes,
        Despesa.data <= fim_mes
    ).all()
    a_pagar_desp = []
    for d in despesas:
        a_pagar_desp.append({
            "id": d.id,
            "tipo": "despesa",
            "descricao": d.descricao,
            "categoria": d.categoria,
            "vencimento": d.data.isoformat(),
            "valor": d.valor,
            "status": "pago"
        })

    total_receber = sum(x["valor"] for x in a_receber)
    total_recebido = sum(x["valor_pago"] for x in a_receber)
    total_pagar_fin = sum(x["valor"] for x in a_pagar_fin)
    total_pagar_desp = sum(x["valor"] for x in a_pagar_desp)

    return {
        "mes": mes,
        "a_receber": a_receber,
        "a_pagar_financiamentos": a_pagar_fin,
        "a_pagar_despesas": a_pagar_desp,
        "resumo": {
            "total_a_receber": total_receber,
            "total_recebido": total_recebido,
            "total_pendente_receber": total_receber - total_recebido,
            "total_a_pagar_financiamentos": total_pagar_fin,
            "total_a_pagar_despesas": total_pagar_desp,
            "total_a_pagar": total_pagar_fin + total_pagar_desp,
            "saldo_mes": total_recebido - (total_pagar_fin + total_pagar_desp)
        }
    }

@router.get("/dre")
def dre_mensal(ano: int = None, db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    if not ano:
        ano = date.today().year
    meses = []
    financiamentos = db.query(Financiamento).all()
    for m in range(1, 13):
        inicio = date(ano, m, 1)
        if m == 12:
            fim = date(ano + 1, 1, 1) - timedelta(days=1)
        else:
            fim = date(ano, m + 1, 1) - timedelta(days=1)

        receita = db.query(func.sum(Parcela.valor_pago)).filter(
            Parcela.data_pagamento >= inicio,
            Parcela.data_pagamento <= fim,
            Parcela.status.in_(["pago", "parcial"])
        ).scalar() or 0

        despesas = db.query(func.sum(Despesa.valor)).filter(
            Despesa.data >= inicio,
            Despesa.data <= fim
        ).scalar() or 0

        # Parcelas de financiamento que venceram neste mês (pagas ou não)
        parcelas_fin = 0
        for f in financiamentos:
            meses_desde_inicio = (inicio.year - f.data_inicio.year) * 12 + (inicio.month - f.data_inicio.month)
            if meses_desde_inicio >= 0 and meses_desde_inicio < f.total_parcelas:
                proxima = f.data_inicio + relativedelta(months=meses_desde_inicio)
                if inicio <= proxima <= fim:
                    parcelas_fin += f.parcela_mensal

        lucro = receita - despesas - parcelas_fin
        meses.append({
            "mes": f"{ano}-{m:02d}",
            "mes_nome": ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"][m-1],
            "receita": round(receita, 2),
            "despesas": round(despesas, 2),
            "parcelas_financiamento": round(parcelas_fin, 2),
            "lucro_liquido": round(lucro, 2)
        })
    return {"ano": ano, "meses": meses}

@router.get("/projecao")
def projecao_6_meses(db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    hoje = date.today()
    projecao = []
    for i in range(6):
        mes_ref = hoje + relativedelta(months=i)
        inicio = date(mes_ref.year, mes_ref.month, 1)
        if mes_ref.month == 12:
            fim = date(mes_ref.year + 1, 1, 1) - timedelta(days=1)
        else:
            fim = date(mes_ref.year, mes_ref.month + 1, 1) - timedelta(days=1)

        receita_prev = db.query(func.sum(Parcela.valor)).filter(
            Parcela.data_vencimento >= inicio,
            Parcela.data_vencimento <= fim,
            Parcela.status.in_(["pendente", "parcial"])
        ).scalar() or 0

        fin_prev = 0
        financiamentos = db.query(Financiamento).filter(
            Financiamento.parcelas_pagas < Financiamento.total_parcelas
        ).all()
        for f in financiamentos:
            meses_desde_inicio = (inicio.year - f.data_inicio.year) * 12 + (inicio.month - f.data_inicio.month)
            if meses_desde_inicio >= 0 and meses_desde_inicio < f.parcelas_restantes:
                proxima = f.data_inicio + relativedelta(months=meses_desde_inicio)
                if inicio <= proxima <= fim:
                    fin_prev += f.parcela_mensal

        saldo = receita_prev - fin_prev
        projecao.append({
            "mes": mes_ref.strftime("%Y-%m"),
            "mes_nome": ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"][mes_ref.month-1],
            "receita_prevista": round(receita_prev, 2),
            "financiamentos_previstos": round(fin_prev, 2),
            "saldo_previsto": round(saldo, 2)
        })
    return projecao
