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

def exigir_admin(usuario=Depends(verificar_token)):
    if not usuario or usuario.get("perfil") != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito ao administrador")
    return usuario

@router.post("/registrar")
def registrar(usuario: UsuarioSchema, db: Session = Depends(get_db), admin=Depends(exigir_admin)):
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

@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == form.username).first()
    if not usuario or not verificar_senha(form.password, usuario.senha):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")
    if not usuario.ativo:
        raise HTTPException(status_code=403, detail="Usuário desativado")
    token = criar_token({"sub": usuario.email, "perfil": usuario.perfil, "nome": usuario.nome})
    return {"access_token": token, "token_type": "bearer"}

@router.get("/eu")
def quem_sou_eu(token: str = Depends(oauth2_scheme)):
    dados = verificar_token(token)
    if not dados:
        raise HTTPException(status_code=401, detail="Token inválido")
    return {"email": dados["sub"], "perfil": dados["perfil"], "nome": dados["nome"]}

@router.get("/usuarios")
def listar_usuarios(db: Session = Depends(get_db), admin=Depends(exigir_admin)):
    usuarios = db.query(Usuario).all()
    return [{"id": u.id, "nome": u.nome, "email": u.email, "perfil": u.perfil, "ativo": u.ativo} for u in usuarios]

@router.delete("/usuarios/{usuario_id}")
def excluir_usuario(usuario_id: int, db: Session = Depends(get_db), admin=Depends(exigir_admin)):
    u = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if u.perfil == "admin":
        raise HTTPException(status_code=400, detail="Não é possível excluir um administrador")
    db.delete(u)
    db.commit()
    return {"mensagem": "Usuário excluído com sucesso"}

@router.put("/usuarios/{usuario_id}/toggle")
def ativar_desativar(usuario_id: int, db: Session = Depends(get_db), admin=Depends(exigir_admin)):
    u = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if u.perfil == "admin":
        raise HTTPException(status_code=400, detail="Não é possível desativar um administrador")
    u.ativo = not u.ativo
    db.commit()
    return {"mensagem": f"Usuário {'ativado' if u.ativo else 'desativado'} com sucesso", "ativo": u.ativo}
