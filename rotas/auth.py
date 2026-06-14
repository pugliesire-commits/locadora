from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from modelos.database import get_db
from modelos.usuario import Usuario
from modelos.seguranca import hash_senha, verificar_senha, criar_token, verificar_token

router = APIRouter(prefix="/auth", tags=["Autenticação"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

class UsuarioSchema(BaseModel):
    nome: str
    email: str
    senha: str
    perfil: Optional[str] = "atendente"

# Cadastrar novo usuário
@router.post("/registrar")
def registrar(usuario: UsuarioSchema, db: Session = Depends(get_db)):
    existente = db.query(Usuario).filter(Usuario.email == usuario.email).first()
    if existente:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    novo = Usuario(
        nome=usuario.nome,
        email=usuario.email,
        senha=hash_senha(usuario.senha),
        perfil=usuario.perfil
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return {"mensagem": "Usuário criado com sucesso", "id": novo.id, "nome": novo.nome}

# Login — retorna o token
@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == form.username).first()
    if not usuario or not verificar_senha(form.password, usuario.senha):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")
    if not usuario.ativo:
        raise HTTPException(status_code=403, detail="Usuário desativado")
    token = criar_token({"sub": usuario.email, "perfil": usuario.perfil, "nome": usuario.nome})
    return {"access_token": token, "token_type": "bearer"}

# Verificar quem está logado
@router.get("/eu")
def quem_sou_eu(token: str = Depends(oauth2_scheme)):
    dados = verificar_token(token)
    if not dados:
        raise HTTPException(status_code=401, detail="Token inválido")
    return {"email": dados["sub"], "perfil": dados["perfil"], "nome": dados["nome"]}