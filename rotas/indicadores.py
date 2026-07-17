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
from typing import Optional

router = APIRouter(prefix="/indicadores", tags=["Indicadores"])

@router.get("/resumo")
def resumo_financeiro(investidor_id: Optional[int] = None, tipo: Optional[str] = None, db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    from modelos.investidor import Investidor
    from fastapi import Query
    # Determinar IDs de veiculos filtrados
    if tipo == "propria":
        ids_veiculos = [v.id for v in db.query(Veiculo).filter(Veiculo.investidor_id == None).all()]
    elif investidor_id:
        ids_veiculos = [v.id for v in db.query(Veiculo).filter(Veiculo.investidor_id == investidor_id).all()]
    else:
        ids_veiculos = None  # sem filtro = todos

    if ids_veiculos is not None:
        locacao_ids = [l.id for l in db.query(Locacao).filter(Locacao.veiculo_id.in_(ids_veiculos)).all()]
        receita_locacoes = db.query(func.sum(Parcela.valor_pago)).filter(
            Parcela.locacao_id.in_(locacao_ids),
            Parcela.status.in_(["pago", "parcial"])
        ).scalar() or 0
        despesas_total = db.query(func.sum(Despesa.valor)).filter(Despesa.veiculo_id.in_(ids_veiculos)).scalar() or 0
        parcelas_total = sum(f.total_pago for f in db.query(Financiamento).filter(Financiamento.veiculo_id.in_(ids_veiculos)).all())
    else:
        locacao_ids = None
        receita_locacoes = db.query(func.sum(Parcela.valor_pago)).filter(Parcela.status.in_(["pago", "parcial"])).scalar() or 0
        despesas_total = db.query(func.sum(Despesa.valor)).scalar() or 0
        parcelas_total = sum(f.total_pago for f in db.query(Financiamento).all())

    total_aportes = (db.query(func.sum(Aporte.valor)).scalar() or 0) if ids_veiculos is None or tipo == "propria" else 0
    receita_total = receita_locacoes + total_aportes
    lucro_liquido = receita_total - despesas_total - parcelas_total
    return {
        "receita_total": receita_total,
        "despesas_total": despesas_total,
        "parcelas_total": parcelas_total,
        "lucro_liquido": lucro_liquido,
        "margem_lucro": round((lucro_liquido / receita_total * 100), 2) if receita_total > 0 else 0
    }

@router.get("/roi-por-veiculo")
def roi_por_veiculo(investidor_id: Optional[int] = None, tipo: Optional[str] = None, db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    if tipo == "propria":
        veiculos = db.query(Veiculo).filter(Veiculo.investidor_id == None).all()
    elif investidor_id:
        veiculos = db.query(Veiculo).filter(Veiculo.investidor_id == investidor_id).all()
    else:
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
def evolucao_mensal(investidor_id: Optional[int] = None, tipo: Optional[str] = None, db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    from modelos.investidor import Investidor
    ano_atual = datetime.now().year
    meses = []
    nomes_meses = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']
    if tipo == "propria":
        ids_veiculos = [v.id for v in db.query(Veiculo).filter(Veiculo.investidor_id == None).all()]
    elif investidor_id:
        ids_veiculos = [v.id for v in db.query(Veiculo).filter(Veiculo.investidor_id == investidor_id).all()]
    else:
        ids_veiculos = None
    financiamentos = db.query(Financiamento).filter(Financiamento.veiculo_id.in_(ids_veiculos)).all() if ids_veiculos is not None else db.query(Financiamento).all()
    for mes in range(1, 13):
        inicio = date(ano_atual, mes, 1)
        if mes == 12:
            fim = date(ano_atual + 1, 1, 1) - relativedelta(days=1)
        else:
            fim = date(ano_atual, mes + 1, 1) - relativedelta(days=1)
        if ids_veiculos is not None:
            locacao_ids = [l.id for l in db.query(Locacao).filter(Locacao.veiculo_id.in_(ids_veiculos)).all()]
            receita_loc = db.query(func.sum(Parcela.valor_pago)).filter(
                Parcela.locacao_id.in_(locacao_ids),
                extract('month', Parcela.data_pagamento) == mes,
                extract('year', Parcela.data_pagamento) == ano_atual,
                Parcela.status.in_(["pago", "parcial"])
            ).scalar() or 0
            despesas = db.query(func.sum(Despesa.valor)).filter(
                Despesa.veiculo_id.in_(ids_veiculos),
                extract('month', Despesa.data) == mes,
                extract('year', Despesa.data) == ano_atual
            ).scalar() or 0
        else:
            receita_loc = db.query(func.sum(Parcela.valor_pago)).filter(
                extract('month', Parcela.data_pagamento) == mes,
                extract('year', Parcela.data_pagamento) == ano_atual,
                Parcela.status.in_(["pago", "parcial"])
            ).scalar() or 0
            despesas = db.query(func.sum(Despesa.valor)).filter(
                extract('month', Despesa.data) == mes,
                extract('year', Despesa.data) == ano_atual
            ).scalar() or 0
        aportes_mes = (db.query(func.sum(Aporte.valor)).filter(
            extract('month', Aporte.data) == mes,
            extract('year', Aporte.data) == ano_atual
        ).scalar() or 0) if ids_veiculos is None or tipo == "propria" else 0
        receita = receita_loc + aportes_mes
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
            "despesas": despesas,
            "financiamentos": parcelas_fin,
            "lucro": receita - despesas - parcelas_fin
        })
    return meses

@router.get("/fluxo-caixa")
def fluxo_caixa(investidor_id: Optional[int] = None, tipo: Optional[str] = None, db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    hoje = date.today()
    inicio_mes = hoje.replace(day=1)
    if tipo == "propria":
        ids_veiculos = [v.id for v in db.query(Veiculo).filter(Veiculo.investidor_id == None).all()]
    elif investidor_id:
        ids_veiculos = [v.id for v in db.query(Veiculo).filter(Veiculo.investidor_id == investidor_id).all()]
    else:
        ids_veiculos = None
    if ids_veiculos is not None:
        locacao_ids = [l.id for l in db.query(Locacao).filter(Locacao.veiculo_id.in_(ids_veiculos)).all()]
        parcelas = db.query(Parcela).filter(
            Parcela.locacao_id.in_(locacao_ids),
            Parcela.data_pagamento >= inicio_mes,
            Parcela.status.in_(["pago", "parcial"])
        ).all()
        despesas = db.query(Despesa).filter(
            Despesa.veiculo_id.in_(ids_veiculos),
            Despesa.data >= inicio_mes
        ).all()
    else:
        parcelas = db.query(Parcela).filter(
            Parcela.data_pagamento >= inicio_mes,
            Parcela.status.in_(["pago", "parcial"])
        ).all()
        despesas = db.query(Despesa).filter(
            Despesa.data >= inicio_mes
        ).all()
    aportes_mes_atual = (db.query(func.sum(Aporte.valor)).filter(
        Aporte.data >= inicio_mes
    ).scalar() or 0) if ids_veiculos is None or tipo == "propria" else 0
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

@router.get("/extrato-frota")
def extrato_frota(tipo: Optional[str] = None, investidor_id: Optional[int] = None, mes: Optional[str] = None, db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    from modelos.investidor import Investidor
    # Determinar veiculos
    if tipo == "propria":
        ids_veiculos = [v.id for v in db.query(Veiculo).filter(Veiculo.investidor_id == None).all()]
        titulo = "Frota Própria"
        comissao_pct = 0
        investidor_nome = None
    elif investidor_id:
        inv = db.query(Investidor).filter(Investidor.id == investidor_id).first()
        ids_veiculos = [v.id for v in db.query(Veiculo).filter(Veiculo.investidor_id == investidor_id).all()]
        titulo = inv.nome if inv else "Investidor"
        comissao_pct = inv.percentual_comissao if inv else 0
        investidor_nome = inv.nome if inv else None
    else:
        ids_veiculos = [v.id for v in db.query(Veiculo).all()]
        titulo = "Todos"
        comissao_pct = 0
        investidor_nome = None
    locacao_ids = [l.id for l in db.query(Locacao).filter(Locacao.veiculo_id.in_(ids_veiculos)).all()]
    # Filtro de mes
    if mes:
        ano, m = int(mes.split("-")[0]), int(mes.split("-")[1])
    else:
        ano, m = None, None
    # Montar lancamentos
    lancamentos = []
    # Entradas: parcelas pagas
    parcelas_q = db.query(Parcela).filter(
        Parcela.locacao_id.in_(locacao_ids),
        Parcela.status.in_(["pago", "parcial"])
    )
    if ano and m:
        parcelas_q = parcelas_q.filter(
            extract('month', Parcela.data_pagamento) == m,
            extract('year', Parcela.data_pagamento) == ano
        )
    for p in parcelas_q.all():
        loc = db.query(Locacao).filter(Locacao.id == p.locacao_id).first()
        cliente = None
        if loc:
            from modelos.cliente import Cliente
            cliente = db.query(Cliente).filter(Cliente.id == loc.cliente_id).first()
        lancamentos.append({
            "data": str(p.data_pagamento),
            "descricao": f"Locação #{p.locacao_id} — {cliente.nome if cliente else 'Cliente'} (Parcela #{p.numero})",
            "entrada": float(p.valor_pago),
            "saida": 0.0,
            "tipo": "entrada"
        })
    # Saidas: despesas
    despesas_q = db.query(Despesa).filter(Despesa.veiculo_id.in_(ids_veiculos))
    if ano and m:
        despesas_q = despesas_q.filter(
            extract('month', Despesa.data) == m,
            extract('year', Despesa.data) == ano
        )
    for d in despesas_q.all():
        vei = db.query(Veiculo).filter(Veiculo.id == d.veiculo_id).first()
        lancamentos.append({
            "data": str(d.data),
            "descricao": f"Despesa — {d.descricao} ({vei.placa if vei else ''})",
            "entrada": 0.0,
            "saida": float(d.valor),
            "tipo": "saida"
        })
    # Saidas: parcelas de financiamento
    fins = db.query(Financiamento).filter(Financiamento.veiculo_id.in_(ids_veiculos)).all()
    for f in fins:
        for i in range(f.parcelas_pagas):
            data_parcela = f.data_inicio + relativedelta(months=i)
            if ano and m:
                if data_parcela.month != m or data_parcela.year != ano:
                    continue
            vei = db.query(Veiculo).filter(Veiculo.id == f.veiculo_id).first()
            lancamentos.append({
                "data": str(data_parcela),
                "descricao": f"Financiamento — {f.banco} ({vei.placa if vei else ''})",
                "entrada": 0.0,
                "saida": float(f.parcela_mensal),
                "tipo": "saida"
            })
    # Aportes (so frota propria ou todos)
    if tipo == "propria" or (tipo is None and investidor_id is None):
        aportes_q = db.query(Aporte)
        if ano and m:
            aportes_q = aportes_q.filter(
                extract('month', Aporte.data) == m,
                extract('year', Aporte.data) == ano
            )
        for a in aportes_q.all():
            lancamentos.append({
                "data": str(a.data),
                "descricao": f"Aporte — {a.descricao}",
                "entrada": float(a.valor),
                "saida": 0.0,
                "tipo": "entrada"
            })
    # Ordenar por data
    lancamentos.sort(key=lambda x: x["data"])
    # Calcular lucro do mes corrente (para comissao)
    total_entradas = sum(l["entrada"] for l in lancamentos)
    total_saidas = sum(l["saida"] for l in lancamentos)
    lucro_mes = total_entradas - total_saidas
    comissao = round(lucro_mes * comissao_pct / 100, 2) if lucro_mes > 0 and comissao_pct > 0 else 0
    # Calcular saldo anterior (meses anteriores ao filtro)
    saldo_anterior = 0.0
    if ano and m:
        # Buscar todos lancamentos antes do mes filtrado
        lanc_anteriores = []
        # Parcelas pagas antes do mes
        parcelas_ant = db.query(Parcela).filter(
            Parcela.locacao_id.in_(locacao_ids),
            Parcela.status.in_(["pago", "parcial"]),
            extract('year', Parcela.data_pagamento) * 12 + extract('month', Parcela.data_pagamento) < ano * 12 + m
        ).all()
        for p in parcelas_ant:
            saldo_anterior += float(p.valor_pago)
        # Despesas antes do mes
        desp_ant = db.query(Despesa).filter(
            Despesa.veiculo_id.in_(ids_veiculos),
            extract('year', Despesa.data) * 12 + extract('month', Despesa.data) < ano * 12 + m
        ).all()
        for d in desp_ant:
            saldo_anterior -= float(d.valor)
        # Parcelas financiamento antes do mes
        for f in fins:
            for i in range(f.parcelas_pagas):
                data_parcela = f.data_inicio + relativedelta(months=i)
                if data_parcela.year * 12 + data_parcela.month < ano * 12 + m:
                    saldo_anterior -= float(f.parcela_mensal)
        # Aportes antes do mes (so frota propria ou todos)
        if tipo == "propria" or (tipo is None and investidor_id is None):
            ap_ant = db.query(Aporte).filter(
                extract('year', Aporte.data) * 12 + extract('month', Aporte.data) < ano * 12 + m
            ).all()
            for a in ap_ant:
                saldo_anterior += float(a.valor)
        # Descontar comissoes dos meses anteriores
        if comissao_pct > 0:
            # Pegar datas distintas com movimento antes do mes filtrado
            from sqlalchemy import distinct
            anos_meses_rec = db.query(
                extract('year', Parcela.data_pagamento).label('ano'),
                extract('month', Parcela.data_pagamento).label('mes')
            ).filter(
                Parcela.locacao_id.in_(locacao_ids),
                Parcela.status.in_(["pago", "parcial"]),
                extract('year', Parcela.data_pagamento) * 12 + extract('month', Parcela.data_pagamento) < ano * 12 + m
            ).distinct().all()
            periodos = set((int(r.ano), int(r.mes)) for r in anos_meses_rec)
            for f in fins:
                for i in range(f.parcelas_pagas):
                    dp = f.data_inicio + relativedelta(months=i)
                    if dp.year * 12 + dp.month < ano * 12 + m:
                        periodos.add((dp.year, dp.month))
            for (ano_i, m_i) in periodos:
                rec_i = db.query(func.sum(Parcela.valor_pago)).filter(
                    Parcela.locacao_id.in_(locacao_ids),
                    Parcela.status.in_(["pago", "parcial"]),
                    extract('year', Parcela.data_pagamento) == ano_i,
                    extract('month', Parcela.data_pagamento) == m_i
                ).scalar() or 0
                desp_i = db.query(func.sum(Despesa.valor)).filter(
                    Despesa.veiculo_id.in_(ids_veiculos),
                    extract('year', Despesa.data) == ano_i,
                    extract('month', Despesa.data) == m_i
                ).scalar() or 0
                fin_i = sum(
                    float(f.parcela_mensal) for f in fins
                    for i in range(f.parcelas_pagas)
                    if (f.data_inicio + relativedelta(months=i)).year == ano_i
                    and (f.data_inicio + relativedelta(months=i)).month == m_i
                )
                lucro_i = float(rec_i) - float(desp_i) - fin_i
                if lucro_i > 0:
                    saldo_anterior -= round(lucro_i * comissao_pct / 100, 2)
        saldo_anterior = round(saldo_anterior, 2)
    # Inserir linha de saldo anterior no inicio
    if ano and m and saldo_anterior != 0:
        mes_ant = m - 1 if m > 1 else 12
        ano_ant = ano if m > 1 else ano - 1
        nomes = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']
        lancamentos.insert(0, {
            "data": f"{ano}-{m:02d}-01",
            "descricao": f"Saldo anterior ({nomes[mes_ant-1]}/{ano_ant})",
            "entrada": saldo_anterior if saldo_anterior > 0 else 0.0,
            "saida": abs(saldo_anterior) if saldo_anterior < 0 else 0.0,
            "tipo": "saldo_anterior"
        })
    # Adicionar comissao como saida (baseada no lucro do mes, nao no saldo anterior)
    if comissao > 0:
        lancamentos.append({
            "data": f"{ano}-{m:02d}-30" if ano and m else str(date.today()),
            "descricao": f"Comissao {investidor_nome} ({comissao_pct}% sobre lucro do mes R$ {lucro_mes:.2f})",
            "entrada": 0.0,
            "saida": comissao,
            "tipo": "comissao"
        })
    # Saldo cumulativo partindo do saldo anterior
    saldo = 0.0
    for l in lancamentos:
        saldo += l["entrada"] - l["saida"]
        l["saldo"] = round(saldo, 2)
    return {
        "titulo": titulo,
        "investidor_nome": investidor_nome,
        "comissao_pct": comissao_pct,
        "lancamentos": lancamentos,
        "total_entradas": round(total_entradas, 2),
        "total_saidas": round(total_saidas + comissao, 2),
        "lucro": round(lucro_mes, 2),
        "comissao": comissao,
        "saldo_final": round(saldo, 2)
    }
@router.get("/dre")
def dre_cascata(veiculo_id: Optional[int] = None, tipo: Optional[str] = None, investidor_id: Optional[int] = None, mes: Optional[str] = None, meses: int = 3, db: Session = Depends(get_db), usuario=Depends(verificar_token)):
    from modelos.investidor import Investidor
    nomes_meses = ['janeiro','fevereiro','marco','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro']
    if mes:
        ano_ref, mes_ref = int(mes.split("-")[0]), int(mes.split("-")[1])
    else:
        hoje = date.today()
        ano_ref, mes_ref = hoje.year, hoje.month
    if meses not in (1, 3, 6, 12):
        meses = 3
    ref = date(ano_ref, mes_ref, 1)
    inicio = ref - relativedelta(months=meses - 1)
    if mes_ref == 12:
        fim = date(ano_ref + 1, 1, 1) - relativedelta(days=1)
    else:
        fim = date(ano_ref, mes_ref + 1, 1) - relativedelta(days=1)
    ym_inicio = inicio.year * 12 + inicio.month
    ym_fim = ano_ref * 12 + mes_ref

    proprios = db.query(Veiculo).filter(Veiculo.investidor_id == None).all()
    num_proprios = len(proprios)
    veiculo_unico = None
    eh_proprio_unico = False
    if veiculo_id:
        veiculo_unico = db.query(Veiculo).filter(Veiculo.id == veiculo_id).first()
        ids_veiculos = [veiculo_id] if veiculo_unico else []
        titulo = f"{veiculo_unico.marca} {veiculo_unico.modelo} ({veiculo_unico.placa})" if veiculo_unico else "Veiculo"
        eh_proprio_unico = veiculo_unico is not None and veiculo_unico.investidor_id is None
    elif tipo == "propria":
        ids_veiculos = [v.id for v in proprios]
        titulo = "Frota Propria"
    elif investidor_id:
        inv = db.query(Investidor).filter(Investidor.id == investidor_id).first()
        ids_veiculos = [v.id for v in db.query(Veiculo).filter(Veiculo.investidor_id == investidor_id).all()]
        titulo = inv.nome if inv else "Investidor"
    else:
        ids_veiculos = [v.id for v in db.query(Veiculo).all()]
        titulo = "Todos os veiculos"

    locacao_ids = [l.id for l in db.query(Locacao).filter(Locacao.veiculo_id.in_(ids_veiculos)).all()] if ids_veiculos else []

    receita = 0.0
    if locacao_ids:
        receita = db.query(func.sum(Parcela.valor_pago)).filter(
            Parcela.locacao_id.in_(locacao_ids),
            Parcela.status.in_(["pago", "parcial"]),
            Parcela.data_pagamento >= inicio,
            Parcela.data_pagamento <= fim
        ).scalar() or 0

    despesas_veiculo = []
    despesas_veiculo_total = 0.0
    if ids_veiculos:
        linhas = db.query(Despesa.categoria, func.sum(Despesa.valor)).filter(
            Despesa.veiculo_id.in_(ids_veiculos),
            Despesa.data >= inicio,
            Despesa.data <= fim
        ).group_by(Despesa.categoria).all()
        for cat, val in linhas:
            despesas_veiculo.append({"categoria": cat or "outros", "valor": round(float(val or 0), 2)})
            despesas_veiculo_total += float(val or 0)

    total_geral = db.query(func.sum(Despesa.valor)).filter(
        Despesa.veiculo_id == None,
        Despesa.data >= inicio,
        Despesa.data <= fim
    ).scalar() or 0
    total_geral = float(total_geral)
    rateio_por_carro = (total_geral / num_proprios) if num_proprios > 0 else 0
    if tipo == "propria":
        despesas_gerais = total_geral
    elif veiculo_id and eh_proprio_unico:
        despesas_gerais = rateio_por_carro
    elif (not veiculo_id) and (not tipo) and (not investidor_id):
        despesas_gerais = total_geral
    else:
        despesas_gerais = 0.0
    despesas_gerais = round(despesas_gerais, 2)

    financiamento = 0.0
    if ids_veiculos:
        fins = db.query(Financiamento).filter(Financiamento.veiculo_id.in_(ids_veiculos)).all()
        for f in fins:
            for i in range(f.parcelas_pagas):
                dp = f.data_inicio + relativedelta(months=i)
                if ym_inicio <= (dp.year * 12 + dp.month) <= ym_fim:
                    financiamento += f.parcela_mensal

    receita = round(float(receita), 2)
    despesas_veiculo_total = round(despesas_veiculo_total, 2)
    financiamento = round(float(financiamento), 2)
    resultado_liquido = round(receita - despesas_veiculo_total - despesas_gerais - financiamento, 2)

    if inicio.year == ano_ref:
        periodo_label = f"{nomes_meses[inicio.month-1]} a {nomes_meses[mes_ref-1]} {ano_ref}"
    else:
        periodo_label = f"{nomes_meses[inicio.month-1]}/{inicio.year} a {nomes_meses[mes_ref-1]}/{ano_ref}"

    return {
        "titulo": titulo,
        "periodo_label": f"{periodo_label} · {meses} meses somados",
        "receita": receita,
        "despesas_veiculo": despesas_veiculo,
        "despesas_veiculo_total": despesas_veiculo_total,
        "despesas_gerais": despesas_gerais,
        "financiamento": financiamento,
        "resultado_liquido": resultado_liquido
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
