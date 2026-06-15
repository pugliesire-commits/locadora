from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from modelos.database import engine, Base
from rotas import veiculos, clientes, locacoes, auth, pagamentos

# Importa todos os modelos para criar as tabelas
from modelos import veiculo, cliente, locacao, usuario, pagamento

# Cria as tabelas no banco automaticamente
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sistema de Locadora de Veículos",
    description="API para gerenciar veículos, clientes e locações",
    version="1.0.0"
)

# Registrando todas as rotas
app.include_router(auth.router)
app.include_router(veiculos.router)
app.include_router(clientes.router)
app.include_router(locacoes.router)
# Serve o frontend
app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/painel")
def painel():
    return FileResponse("index.html")

@app.get("/")
def inicio():
    return {
        "sistema": "Locadora de Veículos",
        "status": "funcionando",
        "versao": "1.0.0"
    }