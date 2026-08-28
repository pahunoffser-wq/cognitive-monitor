# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Выпускная квалификационная работа по курсу "Аналитика данных"
# Проект: Интерактивный монитор когнитивных автоматизмов (Privacy-by-Design)
# Автор: Пахунов Сергей Сергеевич
# Контакты автора: pahunoffser@gmail.com
# Год разработки: 2026
# Все права на архитектуру бэкенда и структуру БД защищены.
# ---------------------------------------------------------------------------

import uuid
import time
from datetime import timezone
from fastapi import FastAPI, Response, Request, Cookie, Depends, HTTPException
from fastapi.responses import HTMLResponse
# <-- ДОБАВЛЕНО: явный импорт Jinja2Templates из fastapi.templating
from fastapi.staticfiles import StaticFiles 
from fastapi.templating import Jinja2Templates 
from pydantic import BaseModel, Field
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker, declarative_base, Session

# Инициализация приложения и шаблонов
app = FastAPI(title="Cognitive Monitor with Analytics")

# Убедитесь, что папка templates существует!
templates = Jinja2Templates(directory="templates")

# Конфигурация SQLite
DATABASE_URL = "sqlite:///./awakening.db"
engine = sa.create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Фабрика сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# --- Модели БД ---
class AnonymizedLog(Base):
    __tablename__ = "anonymized_logs"
    
    id = sa.Column(sa.Integer, primary_key=True, index=True)
    user_uuid = sa.Column(sa.String(36), nullable=False, index=True)
    timestamp = sa.Column(sa.Integer, nullable=False) 
    automatism_type = sa.Column(sa.String(50), nullable=True, index=True)
    trigger_context = sa.Column(sa.String(100), nullable=True)

# Создание таблиц (выполняется один раз при первом запуске скрипта, если таблица не существует)
Base.metadata.create_all(bind=engine)

# --- Схемы Pydantic ---
class LogSchema(BaseModel):
    automatism_log: str = Field(..., description="Тип когнитивного автоматизма")

# --- Утилиты ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Данные об авторе (для передачи в шаблоны)
AUTHOR_INFO = {
    "name": "Пахунов Сергей Сергеевич",
    "email": "pahunoffser@gmail.com",
    "year": 2026,
    "project": "Интерактивный монитор когнитивных автоматизмов"
}

# --- Эндпоинты ---

@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    db = SessionLocal()
    try:
        # Быстрый подсчет без загрузки всех записей в память
        total_logs = db.query(sa.func.count(AnonymizedLog.id)).scalar() or 0
        unique_users = db.query(sa.func.count(AnonymizedLog.user_uuid.distinct())).scalar() or 0
        
        return templates.TemplateResponse(request, "index.html", {
            "request": request, 
            "total_logs": total_logs, 
            "unique_users": unique_users,
            # Передача авторских данных в подвал страницы
            "author_info": AUTHOR_INFO 
        })
    except Exception as e:
        print(f"Database error in index: {e}")
    finally:
        db.close()

@app.post("/api/auth/awaken")
async def authenticate_and_log(data: LogSchema, response: Response):
    db = SessionLocal()
    
    # Логика получения/генерации UUID:
    user_uuid = None
    
    # Попытка получить куку из текущего запроса (если она уже была создана сессией)
    # Примечание: в реальном продакшене лучше использовать Depends(Cookie("user_uuid"))
    if response.headers:
        cookies_str = response.headers.get("cookie", "")
        # Простая парсинг куки (в продакшене используйте библиотеку cookies)
        if "user_uuid=" in cookies_str:
            user_uuid = cookies_str.split("user_uuid=")[1].split(";")[0]

    if not user_uuid:
        # Генерируем новый анонимный идентификатор
        user_uuid = str(uuid.uuid4())
    
    # Создаем запись
    new_log = AnonymizedLog(
        user_uuid=user_uuid,
        timestamp=int(time.time()),
        automatism_type=data.automatism_log,
        trigger_context="Страница входа"
    )
    
    try:
        db.add(new_log)
        db.commit()
        db.refresh(new_log) # Обновляем объект из БД
        
        # Устанавливаем куку, чтобы следующий запрос её "увидел"
        response.set_cookie(
            key="user_uuid", 
            value=user_uuid, 
            httponly=True, 
            samesite="lax",
            max_age=31536000 # 1 год (опционально, для долгосрочной сессии)
        )
        
        return {"status": "success", "message": "Точка присутствия зафиксирована"}
        
    except Exception as e:
        db.rollback() # Откат транзакции при ошибке
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения: {str(e)}")
    finally:
        db.close()

@app.get("/analytics", response_class=HTMLResponse)
async def get_analytics(request: Request):
    db = SessionLocal()
    try:
        # 1. Общая статистика (быстро)
        total_logs = db.query(sa.func.count(AnonymizedLog.id)).scalar() or 0
        
        # Если данных нет, возвращаем пустой шаблон
        if total_logs == 0:
            return templates.TemplateResponse(request, "analytics.html", {
                "request": request, 
                "total_logs": 0, 
                "unique_users": 0, 
                "avg_logs": 0.0,
                "logs": [],
                "hourly_data": [0]* 24,
                # Передача авторских данных в подвал страницы аналитики
                "author_info": AUTHOR_INFO 
            })

        # 2. Уникальные пользователи (быстро)
        unique_users = db.query(sa.func.count(AnonymizedLog.user_uuid.distinct())).scalar() or 0
        
        avg_logs = round(total_logs / unique_users, 2)
        
        # 3. Получаем саму таблицу (с Лимитом, чтобы не убить память!)
        # Берем последние 100 записей для демонстрации
        all_logs = db.query(AnonymizedLog).order_by(sa.desc(AnonymizedLog.timestamp)).limit(100) 
        
        hourly_data = [0]* 24
        processed_logs = []
        
        for log in all_logs:
            # Преобразуем unix timestamp в локальное время сервера
            local_time = time.localtime(log.timestamp)
            
            log_hour = local_time.tm_hour
            hourly_data[log_hour] += 1
            
            # Форматируем для отображения
            formatted_time = time.strftime('%d.%m.%Y %H:%M:%S', local_time)
            
            # Формируем безопасный объект для передачи в шаблон (без direct access к raw DB object)
            processed_log = {
                "id": log.id,
                # В реальном проекте здесь можно хешировать UUID для полной анонимности в UI
                "user_uuid": log.user_uuid[:8], 
                "timestamp_str": formatted_time,
                "automatism_type": log.automatism_type if log.automatism_type else "-",
                "trigger_context": log.trigger_context or "-"
            }
            processed_logs.append(processed_log)
            
        context_data = {
            "total_logs": total_logs,
            "unique_users": unique_users,
            "avg_logs": avg_logs,
            "logs": processed_logs, # Передаем обработанный список, а не сырые объекты БД
            "hourly_data": hourly_data,
            # Передача авторских данных в подвал страницы аналитики
            "author_info": AUTHOR_INFO 
        }
        
        return templates.TemplateResponse(request, "analytics.html", context_data)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка анализа: {str(e)}")
    finally:
        db.close()

# Точка входа в приложение (для запуска через uvicorn)
if __name__ == "__main__":
    import uvicorn
    # Запуск сервера на 8000 порту
    uvicorn.run(app, host="0.0.0.0", port=8000)
