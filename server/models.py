from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, DECIMAL, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from server.db import Base


class Role(Base):
    __tablename__ = "role"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)


class User(Base):
    __tablename__ = "user"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(Integer, ForeignKey("role.id"), nullable=False)
    role_info = relationship("Role", lazy="joined")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, username={self.username}, password={self.hashed_password}, is_active={self.is_active}, role={self.role})>"
    

class Topic(Base):
    __tablename__ = "topic"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True) # Описание может быть пустым
    
    # Связь: у одной темы может быть много уроков
    lessons = relationship("Lesson", back_populates="topic_info", cascade="all, delete-orphan")


class Lesson(Base):
    __tablename__ = "lesson"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False, default="")
    difficult = Column(Integer, nullable=False, index=True)
    rhythm = Column(DECIMAL(), nullable=False)
    notes = Column(JSONB(), nullable=False)
    topic = Column(Integer, nullable=False)

    topic_id = Column(Integer, ForeignKey("topic.id"), nullable=False)
    order_in_topic = Column(Integer, nullable=False, index=True)

    topic_info = relationship("Topic", back_populates="lessons")


class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    __table_args__ = (UniqueConstraint("user_id", "lesson_id", name="uq_user_lesson"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    lesson_id = Column(Integer, ForeignKey("lesson.id"), nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User")
    lesson = relationship("Lesson")




