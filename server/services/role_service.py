from typing import Optional

from models import Role
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# from app.schemas.auth import UserCreate
# from app.utils.security import get_password_hash, verify_password


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_roles(self) -> Optional[Role]:
        """Создание нового пользователя"""
        result = await self.db.execute(select(Role))
        return result.scalars().all()
