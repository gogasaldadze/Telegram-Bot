from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from datetime import datetime
import sqlite3
import asyncio
import httpx
import os
from typing import Optional
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Telegram Reminder Bot")

# Database setup
DB_NAME = "reminders.db"

def init_db():
    """Initialize the database with reminders table"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            chat_id TEXT NOT NULL,
            message TEXT NOT NULL,
            reminder_date TEXT NOT NULL,
            created_at TEXT NOT NULL,
            sent INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()
    logger.info("Database initialized")

init_db()

# Pydantic models
class ReminderRequest(BaseModel):
    message: str
    reminder_date: str  # Format: YYYY-MM-DD HH:MM
    user_id: str
    chat_id: str

class TelegramWebhook(BaseModel):
    update_id: int
    message: Optional[dict] = None

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# Templates
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the web interface"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/set-reminder")
async def set_reminder(reminder: ReminderRequest):
    """Create a new reminder"""
    try:
        # Parse and validate the date
        reminder_datetime = datetime.strptime(reminder.reminder_date, "%Y-%m-%d %H:%M")
        
        # Check if the date is in the future
        if reminder_datetime <= datetime.now():
            raise HTTPException(status_code=400, detail="Reminder date must be in the future")
        
        # Store in database
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO reminders (user_id, chat_id, message, reminder_date, created_at, sent)
            VALUES (?, ?, ?, ?, ?, 0)
        """, (
            reminder.user_id,
            reminder.chat_id,
            reminder.message,
            reminder.reminder_date,
            datetime.now().isoformat()
        ))
        conn.commit()
        reminder_id = cursor.lastrowid
        conn.close()
        
        logger.info(f"Reminder created: ID={reminder_id}, Date={reminder.reminder_date}")
        
        return JSONResponse({
            "success": True,
            "reminder_id": reminder_id,
            "message": "Reminder set successfully!"
        })
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format. Use YYYY-MM-DD HH:MM")
    except Exception as e:
        logger.error(f"Error setting reminder: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/webhook")
async def telegram_webhook(webhook: dict):
    """Handle Telegram webhook updates"""
    # Convert webhook to update format
    update = {"update_id": webhook.get("update_id", 0), "message": webhook.get("message")}
    await handle_telegram_update(update)
    return {"ok": True}

async def send_telegram_message(chat_id: str, text: str, reply_markup: Optional[dict] = None):
    """Send a message via Telegram Bot API"""
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set, cannot send message")
        return
    
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    if reply_markup:
        payload["reply_markup"] = reply_markup
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10.0)
            response.raise_for_status()
            result = response.json()
            if not result.get("ok"):
                logger.error(f"Telegram API error: {result.get('description', 'Unknown error')}")
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text if e.response else str(e)
        logger.error(f"HTTP error sending Telegram message: {error_detail}")
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")

async def check_and_send_reminders():
    """Check for due reminders and send them"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute("""
        SELECT id, user_id, chat_id, message, reminder_date
        FROM reminders
        WHERE sent = 0 AND reminder_date <= ?
    """, (now,))
    
    reminders = cursor.fetchall()
    
    for reminder_id, user_id, chat_id, message, reminder_date in reminders:
        try:
            reminder_text = f"🔔 Reminder!\n\n{message}\n\nDate: {reminder_date}"
            await send_telegram_message(chat_id, reminder_text)
            
            # Mark as sent
            cursor.execute("UPDATE reminders SET sent = 1 WHERE id = ?", (reminder_id,))
            conn.commit()
            
            logger.info(f"Reminder sent: ID={reminder_id}, Chat={chat_id}")
        except Exception as e:
            logger.error(f"Error sending reminder {reminder_id}: {e}")
    
    conn.close()

async def scheduler():
    """Background scheduler to check reminders"""
    while True:
        await asyncio.sleep(60)  # Check every minute
        await check_and_send_reminders()

async def telegram_polling():
    """Poll Telegram for updates"""
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set, skipping polling")
        return
    
    logger.info(f"Starting Telegram polling with token: {TELEGRAM_BOT_TOKEN[:10]}...")
    offset = 0
    while True:
        try:
            url = f"{TELEGRAM_API_URL}/getUpdates"
            params = {"offset": offset, "timeout": 10}
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=15.0)
                response.raise_for_status()
                data = response.json()
            
            if not data.get("ok"):
                logger.error(f"Telegram API error: {data.get('description', 'Unknown error')}")
                await asyncio.sleep(5)
                continue
            
            if data.get("result"):
                for update in data["result"]:
                    offset = update["update_id"] + 1
                    await handle_telegram_update(update)
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if e.response else str(e)
            logger.error(f"HTTP error in polling: {error_detail}")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Error in polling: {e}")
            await asyncio.sleep(5)

async def handle_telegram_update(update: dict):
    """Handle a Telegram update"""
    if "message" not in update:
        return
    
    message = update["message"]
    chat_id = message.get("chat", {}).get("id")
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "")
    
    if not chat_id or not user_id:
        return
    
    # Handle /start command
    if text == "/start":
        welcome_message = (
            "👋 Welcome to Reminder Bot!\n\n"
            "I can help you set reminders. Here's how:\n"
            "1. Use the web interface: /web\n"
            "2. Or send me a message in format:\n"
            "   /remind YYYY-MM-DD HH:MM Your reminder message\n\n"
            "Example: /remind 2024-12-25 10:00 Merry Christmas!\n\n"
            "💡 Tip: Use /chatid to get your Chat ID for the web interface"
        )
        await send_telegram_message(str(chat_id), welcome_message)
    
    # Handle /chatid command
    elif text == "/chatid":
        chat_id_message = (
            f"📱 Your Chat ID: `{chat_id}`\n\n"
            f"👤 Your User ID: `{user_id}`\n\n"
            "Copy your Chat ID and use it in the web interface at:\n"
            "http://localhost:8000"
        )
        await send_telegram_message(str(chat_id), chat_id_message)
    
    # Handle /web command - send web app link
    elif text == "/web":
        web_app_url = os.getenv("WEB_APP_URL", "http://localhost:8000")
        keyboard = {
            "inline_keyboard": [[
                {
                    "text": "Open Reminder App",
                    "web_app": {"url": web_app_url}
                }
            ]]
        }
        await send_telegram_message(str(chat_id), "Click the button below to open the reminder app:", keyboard)
    
    # Handle /remind command
    elif text.startswith("/remind"):
        parts = text.split(" ", 3)
        if len(parts) >= 4:
            date_str = f"{parts[1]} {parts[2]}"
            reminder_message = parts[3]
            
            try:
                reminder_datetime = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
                if reminder_datetime <= datetime.now():
                    await send_telegram_message(str(chat_id), "❌ Reminder date must be in the future!")
                else:
                    # Store reminder
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO reminders (user_id, chat_id, message, reminder_date, created_at, sent)
                        VALUES (?, ?, ?, ?, ?, 0)
                    """, (
                        str(user_id),
                        str(chat_id),
                        reminder_message,
                        date_str,
                        datetime.now().isoformat()
                    ))
                    conn.commit()
                    conn.close()
                    
                    await send_telegram_message(
                        str(chat_id),
                        f"✅ Reminder set for {date_str}!\n\nMessage: {reminder_message}"
                    )
            except ValueError:
                await send_telegram_message(
                    str(chat_id),
                    "❌ Invalid format. Use: /remind YYYY-MM-DD HH:MM Your message"
                )
        else:
            await send_telegram_message(
                str(chat_id),
                "❌ Invalid format. Use: /remind YYYY-MM-DD HH:MM Your message"
            )

@app.on_event("startup")
async def startup_event():
    """Start the scheduler and polling on app startup"""
    logger.info("Starting reminder scheduler...")
    asyncio.create_task(scheduler())
    logger.info("Starting Telegram polling...")
    asyncio.create_task(telegram_polling())

@app.get("/api/reminders/{user_id}")
async def get_user_reminders(user_id: str):
    """Get all reminders for a user"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, message, reminder_date, created_at, sent
        FROM reminders
        WHERE user_id = ?
        ORDER BY reminder_date DESC
    """, (user_id,))
    
    reminders = []
    for row in cursor.fetchall():
        reminders.append({
            "id": row[0],
            "message": row[1],
            "reminder_date": row[2],
            "created_at": row[3],
            "sent": bool(row[4])
        })
    
    conn.close()
    return {"reminders": reminders}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

