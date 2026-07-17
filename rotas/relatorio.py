from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from modelos.database import get_db
from modelos.locacao import Locacao
from modelos.parcela import Parcela
from modelos.financiamento import Financiamento
from modelos.despesa import Despesa
from modelos.aporte import Aporte
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

    aportes_mes = db.query(Aporte).filter(
        Aporte.data >= inicio_mes,
        Aporte.data <= fim_mes
    ).all()
    for a in aportes_mes:
        a_receber.append({
            "id": a.id,
            "tipo": "aporte",
            "descricao": f"💰 {a.descricao}",
            "cliente_id": None,
            "vencimento": a.data.isoformat(),
            "valor": a.valor,
            "valor_pago": a.valor,
            "status": "pago"
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

        receita_loc = db.query(func.sum(Parcela.valor_pago)).filter(
            Parcela.data_pagamento >= inicio,
            Parcela.data_pagamento <= fim,
            Parcela.status.in_(["pago", "parcial"])
        ).scalar() or 0
        aportes_mes = db.query(func.sum(Aporte.valor)).filter(
            Aporte.data >= inicio,
            Aporte.data <= fim
        ).scalar() or 0
        receita = receita_loc + aportes_mes

        despesas = db.query(func.sum(Despesa.valor)).filter(
            Despesa.data >= inicio,
            Despesa.data <= fim
        ).scalar() or 0

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
def projecao_6_meses(tipo: str = None, investidor_id: int = None, db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    from modelos.veiculo import Veiculo
    hoje = date.today()

    proprios = db.query(Veiculo).filter(Veiculo.investidor_id == None).all()
    num_proprios = len(proprios)
    if tipo == "propria":
        ids_veiculos = [v.id for v in proprios]
        rateia_gerais = True
    elif investidor_id:
        ids_veiculos = [v.id for v in db.query(Veiculo).filter(Veiculo.investidor_id == investidor_id).all()]
        rateia_gerais = False
    else:
        ids_veiculos = [v.id for v in db.query(Veiculo).all()]
        rateia_gerais = True

    locacao_ids = [l.id for l in db.query(Locacao).filter(Locacao.veiculo_id.in_(ids_veiculos)).all()] if ids_veiculos else []

    projecao = []
    for i in range(6):
        mes_ref = hoje + relativedelta(months=i)
        inicio = date(mes_ref.year, mes_ref.month, 1)
        if mes_ref.month == 12:
            fim = date(mes_ref.year + 1, 1, 1) - timedelta(days=1)
        else:
            fim = date(mes_ref.year, mes_ref.month + 1, 1) - timedelta(days=1)

        receita_prev = 0
        if locacao_ids:
            receita_prev = db.query(func.sum(Parcela.valor)).filter(
                Parcela.locacao_id.in_(locacao_ids),
                Parcela.data_vencimento >= inicio,
                Parcela.data_vencimento <= fim
            ).scalar() or 0

        despesas_prev = 0
        if ids_veiculos:
            despesas_prev = db.query(func.sum(Despesa.valor)).filter(
                Despesa.veiculo_id.in_(ids_veiculos),
                Despesa.data >= inicio,
                Despesa.data <= fim
            ).scalar() or 0

        gerais_prev = 0
        if rateia_gerais:
            total_geral = db.query(func.sum(Despesa.valor)).filter(
                Despesa.veiculo_id == None,
                Despesa.data >= inicio,
                Despesa.data <= fim
            ).scalar() or 0
            if tipo == "propria" or (not tipo and not investidor_id):
                gerais_prev = float(total_geral)

        fin_prev = 0
        if ids_veiculos:
            financiamentos = db.query(Financiamento).filter(
                Financiamento.veiculo_id.in_(ids_veiculos),
                Financiamento.parcelas_pagas < Financiamento.total_parcelas
            ).all()
            for f in financiamentos:
                meses_desde_inicio = (inicio.year - f.data_inicio.year) * 12 + (inicio.month - f.data_inicio.month)
                if 0 <= meses_desde_inicio < f.total_parcelas:
                    proxima = f.data_inicio + relativedelta(months=meses_desde_inicio)
                    if inicio <= proxima <= fim:
                        fin_prev += f.parcela_mensal

        saidas_prev = round(float(fin_prev) + float(despesas_prev) + float(gerais_prev), 2)
        saldo = round(float(receita_prev) - saidas_prev, 2)

        projecao.append({
            "mes": mes_ref.strftime("%Y-%m"),
            "mes_nome": ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"][mes_ref.month-1],
            "receita_prevista": round(float(receita_prev), 2),
            "financiamentos_previstos": saidas_prev,
            "saldo_previsto": saldo
        })
    return projecao
