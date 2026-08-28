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
import io
import csv
from fastapi import FastAPI, Response, Request, Cookie, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, func
from sqlalchemy.orm import sessionmaker, declarative_base

app = FastAPI(title="Cognitive Monitor with Export")
templates = Jinja2Templates(directory="templates")

DATABASE_URL = "sqlite:///./awakening.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class AnonymizedLog(Base):
    __tablename__ = "anonymized_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_uuid = Column(String, index=True)
    timestamp = Column(Integer)
    automatism_type = Column(String)
    trigger_context = Column(String, nullable=True)

Base.metadata.create_all(bind=engine)

class LogSchema(BaseModel):
    automatism_log: str

# 1. ЖЕСТКИЙ РОУТ ГЛАВНОЙ СТРАНИЦЫ (Прямое чтение строки, 100% запуск дизайна)
@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    db = SessionLocal()
    try:
        total_logs = db.query(AnonymizedLog).count()
        unique_users = db.query(func.count(AnonymizedLog.user_uuid.distinct())).scalar() or 0
        
        # Читаем наш красивый космический HTML-файл напрямую с диска сервера
        with open("templates/index.html", "r", encoding="utf-8") as f:
            html_content = f.read()
            
        # Вручную подставляем живые цифры из базы данных прямо в текст страницы
        html_content = html_content.replace("{{ total_logs }}", str(total_logs))
        html_content = html_content.replace("{{ unique_users }}", str(unique_users))
        
        # Отдаем как чистейший HTMLResponse — браузер ОБЯЗАН включить дизайн!
        return HTMLResponse(content=html_content, status_code=200, headers={"Content-Type": "text/html; charset=utf-8"})
    finally:
        db.close()

# 2. Роут отправки автоматизмов
@app.post("/api/auth/awaken")
async def authenticate_and_log(data: LogSchema, response: Response, user_uuid: str = Cookie(None)):
    db = SessionLocal()
    try:
        if not user_uuid:
            user_uuid = str(uuid.uuid4())
            response.set_cookie(key="user_uuid", value=user_uuid, httponly=True, samesite="lax")
        
        new_log = AnonymizedLog(
            user_uuid=user_uuid,
            timestamp=int(time.time()),
            automatism_type=data.automatism_log,
            trigger_context="Страница входа"
        )
        db.add(new_log)
        db.commit()
        return {"status": "success", "message": "Точка присутствия зафиксирована"}
    finally:
        db.close()

# 3. Роут Админки и Дата-Аналитики
@app.get("/analytics", response_class=HTMLResponse)
async def get_analytics(request: Request):
    db = SessionLocal()
    try:
        total_logs = db.query(AnonymizedLog).count()
        unique_users = db.query(func.count(AnonymizedLog.user_uuid.distinct())).scalar() or 0
        avg_logs = round(total_logs / unique_users, 2) if unique_users > 0 else 0
        all_logs = db.query(AnonymizedLog).order_by(AnonymizedLog.timestamp.desc()).all()
        
        hourly_data = * 24
        for log in all_logs:
            log_hour = time.localtime(log.timestamp).tm_hour
            hourly_data[log_hour] += 1
            log.formatted_time = time.strftime('%d.%m.%Y %H:%M:%S', time.localtime(log.timestamp))
            
        context_data = {
            "total_logs": total_logs,
            "unique_users": unique_users,
            "avg_logs": avg_logs,
            "logs": all_logs,
            "hourly_data": hourly_data
        }
        
        return templates.TemplateResponse(request, "analytics.html", context_data)
    finally:
        db.close()

# 4. Экспорт данных в CSV для Анализа (Excel/Pandas)
@app.get("/api/export")
async def export_data():
    db = SessionLocal()
    try:
        logs = db.query(AnonymizedLog).order_by(AnonymizedLog.timestamp.asc()).all()
        stream = io.StringIO()
        writer = csv.writer(stream, delimiter=';')
        writer.writerow(['ID_Записи', 'Анонимный_ID_Пользователя', 'Unix_Время', 'Дата_и_Время', 'Текст_Автоматизма', 'Контекст'])
        
        for log in logs:
            formatted_time = time.strftime('%d.%m.%Y %H:%M:%S', time.localtime(log.timestamp))
            writer.writerow([log.id, log.user_uuid, log.timestamp, formatted_time, log.automatism_type, log.trigger_context])
            
        stream.seek(0)
        response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
        response.headers["Content-Disposition"] = "attachment; filename=automatisms_dataset.csv"
        return response
    finally:
        db.close()
