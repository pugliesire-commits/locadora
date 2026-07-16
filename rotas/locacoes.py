from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date, timedelta
from modelos.database import get_db
from modelos.locacao import Locacao
from modelos.veiculo import Veiculo
from modelos.pagamento import Pagamento, CobrancaExtra
from modelos.parcela import Parcela

router = APIRouter(prefix="/locacoes", tags=["Locações"])

class LocacaoSchema(BaseModel):
    cliente_id: int
    veiculo_id: int
    data_inicio: str
    data_fim: str
    periodo: str = "diario"
    valor_periodo: float = 0.0
    observacoes: Optional[str] = None

def gerar_parcelas(locacao_id: int, data_inicio: str, data_fim: str, periodo: str, valor_periodo: float, db: Session):
    inicio = datetime.strptime(data_inicio, "%Y-%m-%d").date()
    fim = datetime.strptime(data_fim, "%Y-%m-%d").date()
    parcelas = []
    numero = 1
    data_atual = inicio

    if periodo == "diario":
        while data_atual <= fim:
            parcelas.append(Parcela(
                locacao_id=locacao_id,
                numero=numero,
                data_vencimento=data_atual,
                valor=valor_periodo,
                status="pendente"
            ))
            data_atual += timedelta(days=1)
            numero += 1

    elif periodo == "semanal":
        while data_atual <= fim:
            parcelas.append(Parcela(
                locacao_id=locacao_id,
                numero=numero,
                data_vencimento=data_atual,
                valor=valor_periodo,
                status="pendente"
            ))
            data_atual += timedelta(weeks=1)
            numero += 1

    elif periodo == "mensal":
        while data_atual <= fim:
            parcelas.append(Parcela(
                locacao_id=locacao_id,
                numero=numero,
                data_vencimento=data_atual,
                valor=valor_periodo,
                status="pendente"
            ))
            # Avança um mês mantendo o mesmo dia
            mes = data_atual.month + 1
            ano = data_atual.year
            if mes > 12:
                mes = 1
                ano += 1
            try:
                data_atual = data_atual.replace(year=ano, month=mes)
            except ValueError:
                # Dia não existe no mês (ex: 31 em fevereiro)
                import calendar
                ultimo_dia = calendar.monthrange(ano, mes)[1]
                data_atual = data_atual.replace(year=ano, month=mes, day=ultimo_dia)
            numero += 1

    for p in parcelas:
        db.add(p)

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

    inicio = datetime.strptime(locacao.data_inicio, "%Y-%m-%d")
    fim = datetime.strptime(locacao.data_fim, "%Y-%m-%d")
    dias = (fim - inicio).days
    if dias <= 0:
        raise HTTPException(status_code=400, detail="Data de devolução deve ser após a retirada")

    # Calcula valor total baseado no período
    if locacao.periodo == "diario":
        semanas = dias
        valor_total = dias * locacao.valor_periodo
    elif locacao.periodo == "semanal":
        semanas = dias // 7
        if dias % 7 > 0:
            semanas += 1
        valor_total = semanas * locacao.valor_periodo
    elif locacao.periodo == "mensal":
        meses = dias // 30
        if dias % 30 > 0:
            meses += 1
        valor_total = meses * locacao.valor_periodo
    else:
        valor_total = dias * locacao.valor_periodo

    db_locacao = Locacao(
        cliente_id=locacao.cliente_id,
        veiculo_id=locacao.veiculo_id,
        data_inicio=locacao.data_inicio,
        data_fim=locacao.data_fim,
        dias=dias,
        valor_diaria=veiculo.valor_diaria,
        valor_total=valor_total,
        periodo=locacao.periodo,
        valor_periodo=locacao.valor_periodo,
        observacoes=locacao.observacoes,
        status="Ativa"
    )
    db.add(db_locacao)
    db.flush()  # Gera o ID sem commitar

    # Gera parcelas automaticamente
    gerar_parcelas(
        locacao_id=db_locacao.id,
        data_inicio=locacao.data_inicio,
        data_fim=locacao.data_fim,
        periodo=locacao.periodo,
        valor_periodo=locacao.valor_periodo,
        db=db
    )

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
def devolver_veiculo(id: int, dados: Optional[dict] = None, db: Session = Depends(get_db)):
    locacao = db.query(Locacao).filter(Locacao.id == id).first()
    if not locacao:
        raise HTTPException(status_code=404, detail="Locação não encontrada")
    if locacao.status != "Ativa":
        raise HTTPException(status_code=400, detail="Locação não está ativa")
    dados = dados or {}
    data_str = dados.get("data_recolhimento") or datetime.today().strftime("%Y-%m-%d")
    data_recolhimento = datetime.strptime(data_str, "%Y-%m-%d").date()
    removidas = db.query(Parcela).filter(
        Parcela.locacao_id == id,
        Parcela.status == "pendente",
        Parcela.data_vencimento > data_recolhimento
    ).delete()
    locacao.data_fim = data_str
    locacao.status = "Concluída"
    veiculo = db.query(Veiculo).filter(Veiculo.id == locacao.veiculo_id).first()
    if veiculo:
        veiculo.status = "Disponível"
    db.commit()
    return {
        "mensagem": "Devolução registrada com sucesso",
        "data_recolhimento": data_str,
        "parcelas_futuras_removidas": removidas
    }

@router.delete("/{id}")
def excluir_locacao(id: int, db: Session = Depends(get_db)):
    locacao = db.query(Locacao).filter(Locacao.id == id).first()
    if not locacao:
        raise HTTPException(status_code=404, detail="Locação não encontrada")
    db.query(CobrancaExtra).filter(CobrancaExtra.locacao_id == id).delete()
    db.query(Pagamento).filter(Pagamento.locacao_id == id).delete()
    db.query(Parcela).filter(Parcela.locacao_id == id).delete()
    veiculo = db.query(Veiculo).filter(Veiculo.id == locacao.veiculo_id).first()
    if veiculo:
        veiculo.status = "Disponível"
    db.delete(locacao)
    db.commit()
    return {"mensagem": "Locação excluída com sucesso"}
