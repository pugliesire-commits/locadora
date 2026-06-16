# Financiamentos provisionados
        fin_prev = 0
        financiamentos = db.query(Financiamento).filter(
            Financiamento.parcelas_pagas < Financiamento.total_parcelas
        ).all()
        for f in financiamentos:
            # Calcula qual parcela cairia neste mês da projeção
            meses_desde_inicio = (inicio.year - f.data_inicio.year) * 12 + (inicio.month - f.data_inicio.month)
            if meses_desde_inicio >= 0 and meses_desde_inicio < f.parcelas_restantes:
                proxima = f.data_inicio + relativedelta(months=meses_desde_inicio)
                if inicio <= proxima <= fim:
                    fin_prev += f.parcela_mensal
