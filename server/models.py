"""
SQLAlchemy ORM Models

Модели базы данных для приложения: пользователи, темы, уроки, прогресс.
"""

from sqlalchemy import (
    DECIMAL,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from server.db import Base


class Role(Base):
    """
    Модель роли пользователя.

    Атрибуты:
        id: Уникальный идентификатор
        name: Название роли (уникальное)
    """

    __tablename__ = "role"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name={self.name})>"


class User(Base):
    """
    Модель пользователя.

    Атрибуты:
        id: Уникальный идентификатор
        email: Email пользователя (уникальный)
        username: Имя пользователя (уникальное)
        hashed_password: Хешированный пароль
        is_active: Статус активности
        role: ID роли (внешний ключ)
        role_info: Объект Role через отношение
        created_at: Дата создания (автоматически устанавливается)
    """

    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(Integer, ForeignKey("role.id"), nullable=False)
    role_info = relationship("Role", lazy="joined")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"


class Topic(Base):
    """
    Модель музыкальной темы/раздела.

    Атрибуты:
        id: Уникальный идентификатор
        name: Название темы (уникальное)
        description: Описание темы (опционально)
        lessons: Список связанных уроков (отношение)
    """

    __tablename__ = "topic"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)

    # Связь: у одной темы может быть много уроков
    lessons = relationship(
        "Lesson", back_populates="topic_info", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Topic(id={self.id}, name={self.name})>"


class Lesson(Base):
    """
    Модель урока.

    Атрибуты:
        id: Уникальный идентификатор
        name: Название урока
        description: Описание урока
        difficult: Уровень сложности (числовое значение)
        rhythm: Ритмический паттерн (DECIMAL)
        notes: JSON данные нот (JSONB)
        hand: Рука для игры ("right", "left", "both")
        topic_id: ID темы (внешний ключ)
        order_in_topic: Порядковый номер в теме
        topic_info: Объект Topic через отношение
    """

    __tablename__ = "lesson"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False, default="")
    difficult = Column(Integer, nullable=False, index=True)
    rhythm = Column(DECIMAL(), nullable=False)
    notes = Column(JSONB(), nullable=False)
    hand = Column(String, nullable=False, default="right")
    topic_id = Column(Integer, ForeignKey("topic.id"), nullable=False)
    order_in_topic = Column(Integer, nullable=False, index=True)

    topic_info = relationship("Topic", back_populates="lessons")

    def __repr__(self) -> str:
        return f"<Lesson(id={self.id}, name={self.name}, difficult={self.difficult})>"


class LessonProgress(Base):
    """
    Модель прогресса пользователя по урокам.

    Обеспечивает отслеживание какие уроки пользователь прошёл
    и когда они были завершены.

    Атрибуты:
        id: Уникальный идентификатор
        user_id: ID пользователя (внешний ключ)
        lesson_id: ID урока (внешний ключ)
        completed_at: Дата завершения урока
        user: Объект User через отношение
        lesson: Объект Lesson через отношение

    Ограничения:
        Уникальное ограничение (user_id, lesson_id) - каждый пользователь
        может пройти урок только один раз
    """

    __tablename__ = "lesson_progress"
    __table_args__ = (UniqueConstraint("user_id", "lesson_id", name="uq_user_lesson"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    lesson_id = Column(Integer, ForeignKey("lesson.id"), nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User")
    lesson = relationship("Lesson")

    def __repr__(self) -> str:
        return f"<LessonProgress(user_id={self.user_id}, lesson_id={self.lesson_id}, completed={self.completed_at})>"
