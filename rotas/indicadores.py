from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from modelos.database import get_db
from modelos.locacao import Locacao
from modelos.parcela import Parcela
from modelos.despesa import Despesa
from modelos.financiamento import Financiamento
from modelos.veiculo import Veiculo
from modelos.aporte import Aporte
from modelos.seguranca import verificar_token
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

router = APIRouter(prefix="/indicadores", tags=["Indicadores"])

@router.get("/resumo")
def resumo_financeiro(db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    receita_locacoes = db.query(func.sum(Parcela.valor_pago)).filter(
        Parcela.status.in_(["pago", "parcial"])
    ).scalar() or 0
    total_aportes = db.query(func.sum(Aporte.valor)).scalar() or 0
    receita_total = receita_locacoes + total_aportes
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
    ano_atual = hoje.year
    inicio_ano = date(ano_atual, 1, 1)
    resultado = []
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
        financiamentos = db.query(Financiamento).filter(
            Financiamento.veiculo_id == v.id
        ).all()
        parcelas = 0
        for f in financiamentos:
            for i in range(f.parcelas_pagas):
                data_parcela = f.data_inicio + relativedelta(months=i)
                if inicio_ano <= data_parcela <= hoje:
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
        receita_loc = db.query(func.sum(Parcela.valor_pago)).filter(
            extract('month', Parcela.data_pagamento) == mes,
            extract('year', Parcela.data_pagamento) == ano_atual,
            Parcela.status.in_(["pago", "parcial"])
        ).scalar() or 0
        aportes_mes = db.query(func.sum(Aporte.valor)).filter(
            extract('month', Aporte.data) == mes,
            extract('year', Aporte.data) == ano_atual
        ).scalar() or 0
        receita = receita_loc + aportes_mes
        despesas = db.query(func.sum(Despesa.valor)).filter(
            extract('month', Despesa.data) == mes,
            extract('year', Despesa.data) == ano_atual
        ).scalar() or 0
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
    aportes_mes_atual = db.query(func.sum(Aporte.valor)).filter(
        Aporte.data >= inicio_mes
    ).scalar() or 0
    entradas = sum(p.valor_pago for p in parcelas) + aportes_mes_atual
    saidas = sum(d.valor for d in despesas)
    saldo = entradas - saidas
    return {
        "periodo": f"{inicio_mes.strftime('%d/%m/%Y')} a {hoje.strftime('%d/%m/%Y')}",
        "entradas": entradas,
        "saidas": saidas,
        "saldo": saldo,
        "situacao": "✅ Positivo" if saldo > 0 else "⚠️ Negativo" if saldo < 0 else "➡️ Neutro"
    }

@router.get("/dashboard-frota")
def dashboard_frota(db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    from modelos.investidor import Investidor
    hoje = date.today()
    inicio_mes = hoje.replace(day=1)

    def calcular_bloco(veiculo_ids):
        if not veiculo_ids:
            return {
                "total_veiculos": 0, "disponiveis": 0, "locacoes_ativas": 0,
                "receita_total": 0, "despesas_mes": 0, "valor_em_aberto": 0,
                "parcelas_mes": 0, "financiamentos_ativos": 0, "financiamentos_quitados": 0,
                "total_despesas_geral": 0, "parcelas_pendentes": 0
            }
        veiculos = db.query(Veiculo).filter(Veiculo.id.in_(veiculo_ids)).all()
        disponiveis = sum(1 for v in veiculos if v.status == "Disponível")
        locacoes = db.query(Locacao).filter(
            Locacao.veiculo_id.in_(veiculo_ids),
            Locacao.status == "Ativa"
        ).all()
        todas_locacoes = db.query(Locacao).filter(Locacao.veiculo_id.in_(veiculo_ids)).all()
        todas_locacao_ids = [l.id for l in todas_locacoes]
        receita_total = db.query(func.sum(Parcela.valor_pago)).filter(
            Parcela.locacao_id.in_(todas_locacao_ids),
            Parcela.status.in_(["pago", "parcial"])
        ).scalar() or 0
        despesas_mes = db.query(func.sum(Despesa.valor)).filter(
            Despesa.veiculo_id.in_(veiculo_ids),
            Despesa.data >= inicio_mes
        ).scalar() or 0
        valor_em_aberto = db.query(func.sum(Parcela.valor - Parcela.valor_pago)).filter(
            Parcela.locacao_id.in_(todas_locacao_ids),
            Parcela.status != "pago"
        ).scalar() or 0
        parcelas_pendentes = db.query(func.count(Parcela.id)).filter(
            Parcela.locacao_id.in_(todas_locacao_ids),
            Parcela.status != "pago"
        ).scalar() or 0
        fins = db.query(Financiamento).filter(Financiamento.veiculo_id.in_(veiculo_ids)).all()
        parcelas_mes = 0
        for f in fins:
            meses_desde = (hoje.year - f.data_inicio.year) * 12 + (hoje.month - f.data_inicio.month)
            if 0 <= meses_desde < f.parcelas_pagas:
                parcelas_mes += f.parcela_mensal
        fins_ativos = sum(1 for f in fins if not f.quitado)
        fins_quitados = sum(1 for f in fins if f.quitado)
        total_despesas_geral = db.query(func.sum(Despesa.valor)).filter(
            Despesa.veiculo_id.in_(veiculo_ids)
        ).scalar() or 0
        return {
            "total_veiculos": len(veiculos),
            "disponiveis": disponiveis,
            "locacoes_ativas": len(locacoes),
            "receita_total": round(receita_total, 2),
            "despesas_mes": round(despesas_mes, 2),
            "valor_em_aberto": round(max(0, valor_em_aberto), 2),
            "parcelas_mes": round(parcelas_mes, 2),
            "financiamentos_ativos": fins_ativos,
            "financiamentos_quitados": fins_quitados,
            "total_despesas_geral": round(total_despesas_geral, 2),
            "parcelas_pendentes": parcelas_pendentes
        }

    veiculos_proprios = db.query(Veiculo).filter(Veiculo.investidor_id == None).all()
    ids_proprios = [v.id for v in veiculos_proprios]
    investidores = db.query(Investidor).filter(Investidor.ativo == True).all()
    blocos_investidores = []
    for inv in investidores:
        veiculos_inv = db.query(Veiculo).filter(Veiculo.investidor_id == inv.id).all()
        ids_inv = [v.id for v in veiculos_inv]
        bloco = calcular_bloco(ids_inv)
        bloco["investidor_id"] = inv.id
        bloco["investidor_nome"] = inv.nome
        bloco["investidor_comissao"] = inv.percentual_comissao
        blocos_investidores.append(bloco)

    return {
        "propria": calcular_bloco(ids_proprios),
        "investidores": blocos_investidores
    }
