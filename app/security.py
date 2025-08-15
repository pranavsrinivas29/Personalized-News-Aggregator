import time, jwt, config
from passlib.context import CryptContext

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(p: str) -> str:
    return pwd.hash(p)

def verify_password(p: str, h: str) -> bool:
    return pwd.verify(p, h)

def create_access_token(sub: str) -> str:
    now = int(time.time())
    exp = now + 60 * config.ACCESS_TOKEN_EXPIRES_MINUTES
    payload = {"sub": sub, "iat": now, "exp": exp}
    return jwt.encode(payload, config.JWT_SECRET, algorithm="HS256")

def decode_token(token: str) -> dict:
    return jwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])
