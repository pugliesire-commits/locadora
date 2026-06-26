from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from modelos.database import engine, Base
from rotas import veiculos, clientes, locacoes, auth, pagamentos, financiamento, despesas, indicadores, investidores, parcelas, relatorio, aportes, contratos
from modelos import veiculo, cliente, locacao, usuario, pagamento
from modelos import financiamento as financiamento_model
from modelos import despesa, investidor, lancamento, parcela, aporte

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sistema de Locadora de Veiculos",
    description="API para gerenciar veiculos, clientes e locacoes",
    version="1.0.0"
)

app.include_router(auth.router)
app.include_router(veiculos.router)
app.include_router(clientes.router)
app.include_router(locacoes.router)
app.include_router(pagamentos.router)
app.include_router(financiamento.router)
app.include_router(despesas.router)
app.include_router(indicadores.router)
app.include_router(investidores.router)
app.include_router(parcelas.router)
app.include_router(relatorio.router)
app.include_router(aportes.router)
app.include_router(contratos.router)

app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/painel")
def painel():
    return FileResponse("index.html")

@app.get("/contrato/{locacao_id}", response_class=HTMLResponse)
async def ver_contrato(locacao_id: int):
    from modelos.database import SessionLocal
    from rotas.contratos import gerar_contrato
    db = SessionLocal()
    try:
        return gerar_contrato(locacao_id, db)
    finally:
        db.close()

@app.get("/")
def inicio():
    return {
        "sistema": "Locadora de Veiculos",
        "status": "funcionando",
        "versao": "1.0.0"
    }
