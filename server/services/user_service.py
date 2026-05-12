"""
User Service Module

Обеспечивает бизнес-логику для работы с пользователями:
регистрация, аутентификация, обновление данных.
"""

import logging
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.auth import UserCreate, UserUpdate
from server.models import Role, User
from server.utils.security import get_password_hash, verify_password

logger = logging.getLogger(__name__)


class UserService:
    """
    Сервис для управления пользователями.

    Предоставляет методы для:
    - Создания новых пользователей
    - Поиска пользователей по различным критериям
    - Аутентификации
    - Обновления данных пользователей
    """

    DEFAULT_USER_ROLE: str = "пользователь"
    """Роль по умолчанию для новых пользователей"""

    def __init__(self, db: AsyncSession) -> None:
        """
        Инициализация сервиса.

        Аргументы:
            db: Асинхронная сессия БД
        """
        self.db = db

    async def create_user(self, user_data: UserCreate) -> Optional[User]:
        """
        Создаёт нового пользователя.

        Аргументы:
            user_data: Данные для создания (Pydantic модель UserCreate)

        Возвращает:
            Созданный объект User или None при ошибке дублирования

        Исключения:
            Откатывает транзакцию при IntegrityError (дублирование email/username)
        """
        try:
            hashed_password = get_password_hash(user_data.password)

            # Получаем ID роли по умолчанию
            result = await self.db.execute(
                select(Role.id).where(Role.name == self.DEFAULT_USER_ROLE)
            )
            role_id = result.scalar_one_or_none()

            if not role_id:
                logger.error(f"Роль '{self.DEFAULT_USER_ROLE}' не найдена в БД")
                return None

            # Создаём новый объект User
            db_user = User(
                email=user_data.email,
                username=user_data.username,
                hashed_password=hashed_password,
                role=role_id,
            )

            self.db.add(db_user)
            await self.db.commit()
            await self.db.refresh(db_user)

            logger.info(f"Пользователь создан: {user_data.email}")
            return db_user

        except IntegrityError as e:
            await self.db.rollback()
            logger.warning(f"Ошибка дублирования при создании пользователя: {str(e)}")
            return None
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Ошибка при создании пользователя: {str(e)}")
            return None

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Получает пользователя по email.

        Аргументы:
            email: Email пользователя

        Возвращает:
            Объект User или None если не найден
        """
        try:
            result = await self.db.execute(select(User).where(User.email == email))
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Ошибка при поиске пользователя по email: {str(e)}")
            return None

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Получает пользователя по имени.

        Аргументы:
            username: Имя пользователя

        Возвращает:
            Объект User или None если не найден
        """
        try:
            result = await self.db.execute(
                select(User).where(User.username == username)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Ошибка при поиске пользователя по username: {str(e)}")
            return None

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Получает пользователя по ID.

        Аргументы:
            user_id: ID пользователя

        Возвращает:
            Объект User или None если не найден
        """
        try:
            result = await self.db.execute(select(User).where(User.id == user_id))
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Ошибка при поиске пользователя по ID: {str(e)}")
            return None

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Аутентифицирует пользователя по email и паролю.

        Аргументы:
            email: Email пользователя
            password: Открытый пароль

        Возвращает:
            Объект User если аутентификация успешна, иначе None
        """
        user = await self.get_user_by_email(email)

        if not user:
            logger.warning(f"Попытка входа с несуществующим email: {email}")
            return None

        if not verify_password(password, user.hashed_password):
            logger.warning(f"Неверный пароль для пользователя: {email}")
            return None

        if not user.is_active:
            logger.warning(f"Попытка входа неактивного пользователя: {email}")
            return None

        logger.info(f"Пользователь успешно аутентифицирован: {email}")
        return user

    async def update_user(
        self, user_id: int, update_data: UserUpdate
    ) -> Optional[User]:
        """
        Обновляет данные пользователя.

        Аргументы:
            user_id: ID пользователя
            update_data: Данные для обновления (Pydantic модель UserUpdate)

        Возвращает:
            Обновлённый объект User или None при ошибке
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            logger.warning(
                f"Попытка обновления несуществующего пользователя ID: {user_id}"
            )
            return None

        try:
            # Обновляем только переданные поля
            if update_data.username:
                user.username = update_data.username
            if update_data.email:
                user.email = update_data.email
            if update_data.password:
                user.hashed_password = get_password_hash(update_data.password)
            if hasattr(update_data, "is_active") and update_data.is_active is not None:
                user.is_active = update_data.is_active

            await self.db.commit()
            await self.db.refresh(user)

            logger.info(f"Пользователь обновлён: ID {user_id}")
            return user

        except IntegrityError as e:
            await self.db.rollback()
            logger.warning(
                f"Ошибка при обновлении пользователя (дублирование): {str(e)}"
            )
            return None
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Ошибка при обновлении пользователя: {str(e)}")
            return None

    async def get_all_users(self) -> List[User]:
        """
        Получает список всех пользователей.

        Используется в админ-панели для отображения списка пользователей.

        Возвращает:
            Список объектов User, отсортированных по ID
        """
        try:
            result = await self.db.execute(select(User).order_by(User.id))
            users = result.scalars().all()
            logger.debug(f"Получены данные {len(users)} пользователей")
            return users
        except Exception as e:
            logger.error(f"Ошибка при получении списка пользователей: {str(e)}")
            return []
