from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from typing import Optional
from models import User, Role
from schemas.auth import UserCreate, UserUpdate
from utils.security import get_password_hash, verify_password

class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_user(self, user_data: UserCreate) -> Optional[User]:
        """Создание нового пользователя"""
        try:
            hashed_password = get_password_hash(user_data.password)
            result = await self.db.execute(
            select(Role.id).where(Role.name == "пользователь")
            )
            role_id = result.scalar_one_or_none()
            db_user = User(
                email=user_data.email,
                username=user_data.username,
                hashed_password=hashed_password,
                role=role_id
            )
            self.db.add(db_user)
            await self.db.commit()
            await self.db.refresh(db_user)
            return db_user
        except IntegrityError:
            await self.db.rollback()
            return None
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        # Запрашиваем ТОЛЬКО User. Благодаря lazy="joined" в модели, 
        # роль подтянется автоматически.
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        # Снова используем scalar_one_or_none(), так как мы запрашиваем 
        # только одну сущность (User), а не две раздельные
        return result.scalar_one_or_none()
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Получение пользователя по email"""
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_id(self, user_id: int):
        """Получение пользователя по ID"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        # Снова используем scalar_one_or_none(), так как мы запрашиваем 
        # только одну сущность (User), а не две раздельные
        return result.scalar_one_or_none()
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Аутентификация пользователя"""
        user = await self.get_user_by_email(email)
        print(user)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
    

    
    async def update_user(self, user_id: int, update_data: UserUpdate) -> Optional[User]:
        """Обновление данных пользователя"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None
            
        if update_data.username:
            user.username = update_data.username
        if update_data.email:
            user.email = update_data.email
        if update_data.password:
            user.hashed_password = get_password_hash(update_data.password)
        if getattr(update_data, "is_active", None) is not None:
            user.is_active = update_data.is_active
            
        try:
            await self.db.commit()
            await self.db.refresh(user)
            return user
        except IntegrityError:
            await self.db.rollback()
            return None
        
    async def get_all_users(self):
        """Получение списка всех пользователей для админ-панели"""
        result = await self.db.execute(
            select(User).order_by(User.id)
        )
        return result.scalars().all()