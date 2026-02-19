from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from core.config import settings

def create_access_token(data: Dict[str, Any]) -> str:
    """Создание access токена"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS * 5)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """Проверка и декодирование токена"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        # Проверяем срок действия
        exp = payload.get("exp")
        if exp is None or datetime.now(timezone.utc) > datetime.fromtimestamp(exp):
            return None
        return payload.get("user_id")
    except JWTError:
        return None

def get_user_id_from_token(token: str) -> Optional[int]:
    """Извлечение ID пользователя из токена"""
    payload = verify_token(token)
    if payload:
        return payload.get("user_id")
    return None