from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext

# Chave secreta para assinar os tokens
SECRET_KEY = "locadora-chave-secreta-2024-mude-em-producao"
ALGORITHM = "HS256"
EXPIRACAO_MINUTOS = 480  # 8 horas

# Configuração do hash de senha
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_senha(senha: str) -> str:
    """Transforma a senha em código secreto"""
    return pwd_context.hash(senha)

def verificar_senha(senha: str, hash: str) -> bool:
    """Verifica se a senha digitada bate com o hash"""
    return pwd_context.verify(senha, hash)

def criar_token(dados: dict) -> str:
    """Cria um token JWT com os dados do usuário"""
    payload = dados.copy()
    expiracao = datetime.utcnow() + timedelta(minutes=EXPIRACAO_MINUTOS)
    payload.update({"exp": expiracao})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verificar_token(token: str) -> dict:
    """Verifica se o token é válido e retorna os dados"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None