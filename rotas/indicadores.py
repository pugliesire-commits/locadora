from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from modelos.database import get_db
from modelos.locacao import Locacao
from modelos.parcela import Parcela
from modelos.despesa import Despesa
from modelos.financiamento import Financiamento
from modelos.veiculo import Veiculo
from modelos.seguranca import verificar_token
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

router = APIRouter(prefix="/indicadores", tags=["Indicadores"])

@router.get("/resumo")
def resumo_financeiro(db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    receita_total = db.query(func.sum(Parcela.valor_pago)).filter(
        Parcela.status.in_(["pago", "parcial"])
    ).scalar() or 0
    despesas_total = db.query(func.sum(Despesa.valor)).scalar() or 0
    parcelas_total = sum(f.total_pago for f in db.query(Financiamento).all())
    lucro_liquido = receita_total - despesas_total - parcelas_total
    return {
        "receita_total": receita_total,
        "despesas_total": despesas_total,
        "parcelas_total": parcelas_total,
        "lucro_liquido": lucro_liquido,
        "margem_lucro": round((lucro_liquido / receita_total * 100), 2) if receita_total > 0 else 0
    }

@router.get("/roi-por-veiculo")
def roi_por_veiculo(db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    veiculos = db.query(Veiculo).all()
    resultado = []
    hoje = date.today()
    for v in veiculos:
        receita = db.query(func.sum(Parcela.valor_pago)).join(
            Locacao, Parcela.locacao_id == Locacao.id
        ).filter(
            Locacao.veiculo_id == v.id,
            Parcela.status.in_(["pago", "parcial"])
        ).scalar() or 0
        despesas = db.query(func.sum(Despesa.valor)).filter(
            Despesa.veiculo_id == v.id
        ).scalar() or 0
        # Parcelas de financiamento pagas até hoje
        financiamentos = db.query(Financiamento).filter(
            Financiamento.veiculo_id == v.id
        ).all()
        parcelas = 0
        for f in financiamentos:
            for i in range(f.parcelas_pagas):
                data_parcela = f.data_inicio + relativedelta(months=i)
                if data_parcela <= hoje:
                    parcelas += f.parcela_mensal
        custo_total = despesas + parcelas
        lucro = receita - custo_total
        roi = round((lucro / custo_total * 100), 2) if custo_total > 0 else 0
        resultado.append({
            "veiculo_id": v.id,
            "placa": v.placa,
            "marca": v.marca,
            "modelo": v.modelo,
            "receita": receita,
            "despesas": despesas,
            "parcelas": parcelas,
            "custo_total": custo_total,
            "lucro": lucro,
            "roi": roi,
            "situacao": "✅ Lucrativo" if lucro > 0 else "⚠️ Prejuízo" if lucro < 0 else "➡️ Neutro"
        })
    return sorted(resultado, key=lambda x: x["roi"], reverse=True)

@router.get("/evolucao-mensal")
def evolucao_mensal(db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    ano_atual = datetime.now().year
    meses = []
    nomes_meses = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']
    financiamentos = db.query(Financiamento).all()
    for mes in range(1, 13):
        inicio = date(ano_atual, mes, 1)
        if mes == 12:
            fim = date(ano_atual + 1, 1, 1) - relativedelta(days=1)
        else:
            fim = date(ano_atual, mes + 1, 1) - relativedelta(days=1)
        receita = db.query(func.sum(Parcela.valor_pago)).filter(
            extract('month', Parcela.data_pagamento) == mes,
            extract('year', Parcela.data_pagamento) == ano_atual,
            Parcela.status.in_(["pago", "parcial"])
        ).scalar() or 0
        despesas = db.query(func.sum(Despesa.valor)).filter(
            extract('month', Despesa.data) == mes,
            extract('year', Despesa.data) == ano_atual
        ).scalar() or 0
        # Parcelas de financiamento que venceram neste mês
        parcelas_fin = 0
        for f in financiamentos:
            meses_desde_inicio = (inicio.year - f.data_inicio.year) * 12 + (inicio.month - f.data_inicio.month)
            if meses_desde_inicio >= 0 and meses_desde_inicio < f.parcelas_pagas:
                proxima = f.data_inicio + relativedelta(months=meses_desde_inicio)
                if inicio <= proxima <= fim:
                    parcelas_fin += f.parcela_mensal
        meses.append({
            "mes": nomes_meses[mes-1],
            "numero": mes,
            "receita": receita,
            "despesas": despesas + parcelas_fin,
            "lucro": receita - despesas - parcelas_fin
        })
    return meses

@router.get("/fluxo-caixa")
def fluxo_caixa(db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    hoje = date.today()
    inicio_mes = hoje.replace(day=1)
    parcelas = db.query(Parcela).filter(
        Parcela.data_pagamento >= inicio_mes,
        Parcela.status.in_(["pago", "parcial"])
    ).all()
    despesas = db.query(Despesa).filter(
        Despesa.data >= inicio_mes
    ).all()
    entradas = sum(p.valor_pago for p in parcelas)
    saidas = sum(d.valor for d in despesas)
    saldo = entradas - saidas
    return {
        "periodo": f"{inicio_mes.strftime('%d/%m/%Y')} a {hoje.strftime('%d/%m/%Y')}",
        "entradas": entradas,
        "saidas": saidas,
        "saldo": saldo,
        "situacao": "✅ Positivo" if saldo > 0 else "⚠️ Negativo" if saldo < 0 else "➡️ Neutro"
    }
