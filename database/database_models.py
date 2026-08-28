"""
database/database_models.py - Модели данных SQLAlchemy.

Хранит структуру таблицы для обезличенных логов автоматизмов.
"""

from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class AnonymizedLog(Base):
    """
    Модель таблицы для хранения обезличенных данных о когнитивных автоматизмах.
    
    Поля:
    - id: Первичный ключ (автогенерируется БД).
    - session_id: Уникальный анонимный идентификатор (UUID4). Связывает данные с сессией.
    - automatism_text: Текст описания автоматизма (например, "Я проверяю телефон").
    - awareness_level: Уровень осознанности от 1 до 5.
    - context: Контекст возникновения (work/home/transport).
    - created_at: Время создания записи.
    
    Примечание: В этой модели нет полей для хранения личных данных (имя, email),
    что соответствует принципу Privacy-by-Design.
    """
    
    __tablename__ = "anonymized_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), nullable=False, unique=True) # UUID строка
    automatism_text = Column(Text, nullable=False)
    awareness_level = Column(Integer, nullable=False) # 1-5
    context = Column(String(50), nullable=False) # Работа, Дом, Транспорт
    created_at = Column(Integer, default=0) # Захраним timestamp в секундах для простоты с SQLite

    def __repr__(self):
        return f"<Log(session_id={self.session_id}, level={self.awareness_level})>"
