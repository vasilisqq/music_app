from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict
from schemas.auth import UserLogin
from models import User
from services.user_service import UserService
from server.core.config import settings
from utils.jwt import create_access_token

class AuthService:
    def __init__(self, db: AsyncSession):
        self.user_service = UserService(db)

    async def login_user(self, user_data: UserLogin) -> Optional[User]:
        # 1. Аутентификация пользователя
        user = await self.user_service.authenticate_user(
            user_data.email, user_data.password
        )
        if not user or not user.is_active:
            return None

        return create_access_token(data = {"user_id": str(user.id)})

    #async def logout_user(self, refresh_token: str) -> bool:
    #    """Выход пользователя (удаление refresh токена)."""
    #    payload = verify_token(refresh_token, token_type="refresh")
    #    if not payload:
    #        return False
        
    #    user_id = payload.get("sub")
    #    if user_id:
    #        await redis_client.delete_refresh_token(int(user_id))
    #        return True
    #    return False
        
        
        

