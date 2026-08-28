# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Выпускная квалификационная работа по курсу "Аналитика данных"
# Проект: Интерактивный монитор когнитивных автоматизмов (Privacy-by-Design)
# Автор: Пахунов Сергей Сергеевич
# Контакты автора: pahunoffser@gmail.com
# Год разработки: 2026
# Все права на архитектуру бэкенда и структуру БД защищены.
# ---------------------------------------------------------------------------

import uuid, time, io, csv
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

# ЭТАЛОННЫЙ HTML-КОД С ОБНОВЛЕНИЕМ СЧЕТЧИКОВ БЕЗ ПЕРЕЗАГРУЗКИ
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Монитор Автоматизмов</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background: linear-gradient(125deg, #0d1117, #161b22, #070a0e, #1a2332);
            background-size: 400% 400%; animation: gradientMove 15s ease infinite; color: #c9d1d9;
            font-family: -apple-system, sans-serif; display: flex; flex-direction: column; justify-content: center; align-items: center; min-height: 100vh; padding: 20px; user-select: none; position: relative; overflow-x: hidden;
        }
        body::before {
            content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background-image: radial-gradient(white, rgba(255,255,255,.15) 2px, transparent 40px); background-size: 550px 550px; opacity: 0.15; z-index: 0;
        }
        @keyframes gradientMove { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }
        .grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; max-width: 550px; width: 100%; margin-bottom: 50px; z-index: 1; }
        .card { background: rgba(22, 27, 34, 0.7); border: 1px solid rgba(48, 54, 61, 0.8); border-radius: 12px; padding: 15px; text-align: center; backdrop-filter: blur(8px); }
        .card h3 { font-size: 0.8rem; color: #8b949e; text-transform: uppercase; margin-bottom: 5px; }
        .card p { font-size: 1.6rem; font-weight: bold; color: #58a6ff; }
        .container { text-align: center; max-width: 550px; width: 100%; transition: all 0.4s ease-in-out; margin-bottom: 40px; z-index: 1; }
        h1 { font-size: 1.8rem; font-weight: 300; line-height: 1.6; margin-bottom: 40px; color: #f0f6fc; }
        .btn-action { background: rgba(22, 27, 34, 0.4); border: 1px solid #30363d; color: #8b949e; padding: 14px 40px; font-size: 0.95rem; border-radius: 30px; cursor: pointer; transition: all 0.4s ease; backdrop-filter: blur(4px); }
        .btn-action:hover { border-color: #58a6ff; color: #ffffff; box-shadow: 0 0 25px rgba(88, 166, 255, 0.2); }
        .input-wrapper { margin-bottom: 30px; }
        .input-field { width: 100%; background: rgba(22, 27, 34, 0.8); border: 1px solid #30363d; border-radius: 12px; padding: 18px; color: #f0f6fc; font-size: 1.05rem; outline: none; text-align: center; }
        .hidden { display: none !important; }
        footer { text-align: center; padding: 20px; margin-top: auto; border-top: 1px solid rgba(48, 54, 61, 0.5); color: #8b949e; font-size: 0.85rem; width: 100%; max-width: 550px; z-index: 1; }
    </style>
</head>
<body>
    <div class="grid">
        <div class="card"><h3>Всего фиксаций в мире</h3><p id="stat-total">{{ total_logs }}</p></div>
        <div class="card"><h3>Проснувшихся разумов</h3><p id="stat-users">{{ unique_users }}</p></div>
    </div>
    
    <div class="container" id="screen-1">
        <h1>Остановитесь на мгновение.<br>Где блуждали ваши мысли секунду назад?</h1>
        <button class="btn-action" onclick="goToStep2()">Я здесь</button>
    </div>
    
    <div class="container hidden" id="screen-2">
        <h1 style="font-size: 1.4rem; margin-bottom: 35px;">В каком ментальном автоматизме вы поймали себя прямо сейчас?</h1>
        <div class="input-wrapper"><input type="text" id="awareness-input" class="input-field" placeholder="Например: листаю ленту..." autocomplete="off"></div>
        <button class="btn-action" onclick="authenticateUser()">Войти в присутствие</button>
    </div>

    <div class="container hidden" id="screen-3">
        <h1 style="font-size: 2rem; color: #58a6ff; margin-bottom: 20px;">✓ Вы в моменте.</h1>
        <p style="font-size: 1.1rem; color: #8b949e; line-height: 1.6;">Фиксация успешно сохранена в анонимную базу данных.<br>Возвращайтесь к реальной жизни.</p>
    </div>

    <footer>
        <p>© 2026 Монитор Осознанности. Разработчик: <strong>Пахунов С. С.</strong></p>
        <p style="font-size: 0.75rem; margin-top: 5px; color: #484f58;">Выпускная квалификационная работа | Аналитика данных</p>
    </footer>

    <script>
        function goToStep2() {
            document.getElementById('screen-1').classList.add('hidden');
            document.getElementById('screen-2').classList.remove('hidden');
            document.getElementById('awareness-input').focus();
        }
        
        function authenticateUser() {
            const userInput = document.getElementById('awareness-input').value.trim();
            if (!userInput) { alert('Введите автоматизм'); return; }
            
            fetch('/api/auth/awaken', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ automatism_log: userInput })
            })
            .then(res => res.json())
            .then(data => {
                document.getElementById('screen-2').classList.add('hidden');
                document.getElementById('screen-3').classList.remove('hidden');
                
                const totalElem = document.getElementById('stat-total');
                if (totalElem) {
                    let currentTotal = parseInt(totalElem.innerText) || 0;
                    totalElem.innerText = currentTotal + 1;
                }
            })
            .catch(err => alert('Ошибка соединения с сервером.'));
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    db = SessionLocal()
    try:
        total_logs = db.query(AnonymizedLog).count()
        unique_users = db.query(func.count(AnonymizedLog.user_uuid.distinct())).scalar() or 0
        html_content = HTML_TEMPLATE.replace("{{ total_logs }}", str(total_logs)).replace("{{ unique_users }}", str(unique_users))
        return HTMLResponse(content=html_content, status_code=200, headers={"Content-Type": "text/html; charset=utf-8"})
    finally:
        db.close()

@app.post("/api/auth/awaken")
async def authenticate_and_log(data: LogSchema, response: Response, user_uuid: str = Cookie(None)):
    db = SessionLocal()
    try:
        if not user_uuid:
            user_uuid = str(uuid.uuid4())
            response.set_cookie(key="user_uuid", value=user_uuid, httponly=True, samesite="lax")
        new_log = AnonymizedLog(user_uuid=user_uuid, timestamp=int(time.time()), automatism_type=data.automatism_log, trigger_context="Страница входа")
        db.add(new_log)
        db.commit()
        return {"status": "success", "message": "Фиксация успешна"}
    finally:
        db.close()

@app.get("/analytics", response_class=HTMLResponse)
async def get_analytics(request: Request):
    db = SessionLocal()
    try:
        total_logs = db.query(AnonymizedLog).count()
        unique_users = db.query(func.count(AnonymizedLog.user_uuid.distinct())).scalar() or 0
        avg_logs = round(total_logs / unique_users, 2) if unique_users > 0 else 0
        all_logs = db.query(AnonymizedLog).order_by(AnonymizedLog.timestamp.desc()).all()
        hourly_data = [0] * 24
        for log in all_logs:
            log_hour = time.localtime(log.timestamp).tm_hour
            hourly_data[log_hour] += 1
            log.formatted_time = time.strftime('%d.%m.%Y %H:%M:%S', time.localtime(log.timestamp))
        context_data = {"total_logs": total_logs, "unique_users": unique_users, "avg_logs": avg_logs, "logs": all_logs, "hourly_data": hourly_data}
        return templates.TemplateResponse(request, "analytics.html", context_data)
    finally:
        db.close()

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

