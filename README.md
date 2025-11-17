# Telegram Reminder Bot

A FastAPI-based Telegram bot that allows you to set custom reminders and receive them at specified dates and times.

## Features

- Set custom reminders with messages and specific dates/times
- Web interface for setting reminders
- Telegram bot commands for quick reminder setup
- Telegram Web App integration
- Automatic reminder delivery at scheduled times
- View all your reminders

## Prerequisites

Before you start, make sure you have:
- Python 3.8 or higher installed
- A Telegram account

## Step-by-Step Setup Guide

### Step 1: Clone the Repository

If you're cloning this repository, run:

```bash
git clone <repository-url>
cd Telegram-Bot
```

### Step 2: Create a Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Start a conversation and send the command `/newbot`
3. Follow the instructions:
   - Choose a name for your bot (e.g., "My Reminder Bot")
   - Choose a username for your bot (must end with "bot", e.g., "my_reminder_bot")
4. BotFather will give you a token that looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`
5. Copy this token - you'll need it in the next step

### Step 3: Install Python Dependencies

Open your terminal/command prompt in the project directory and run:

```bash
pip install -r requirements.txt
```

This will install all required packages including FastAPI, uvicorn, and other dependencies.

### Step 4: Configure Environment Variables

Create a file named `.env` in the project root directory (same folder as `main.py`).

On Windows, you can create it using:
```bash
notepad .env
```

On Linux/Mac:
```bash
nano .env
```

Add the following content to the `.env` file:

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
WEB_APP_URL=http://localhost:8000
```

Replace `your_bot_token_here` with the actual token you received from BotFather in Step 2.

Example:
```
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
WEB_APP_URL=http://localhost:8000
```

Important: Keep your `.env` file private and never commit it to version control. It contains your bot token which is like a password.

### Step 5: Run the Application

Start the server by running:

```bash
python main.py
```

You should see output indicating the server is starting. The application will be available at `http://localhost:8000`.

Alternatively, you can run it with uvicorn directly:

```bash
uvicorn main:app --reload
```

The `--reload` flag enables auto-reload when you make code changes (useful for development).

### Step 6: Test Your Bot

1. Open Telegram and search for your bot using the username you created (e.g., `@my_reminder_bot`)
2. Start a conversation with your bot
3. Send the command `/start`
4. Your bot should reply with a welcome message and instructions

If the bot responds, congratulations! Your setup is working.

## How to Use

### Setting Reminders via Telegram

You can set reminders directly in Telegram by sending commands to your bot:

**Get started:**
```
/start
```

**Get your Chat ID (needed for web interface):**
```
/chatid
```

**Set a reminder:**
```
/remind 2024-12-25 10:00 Merry Christmas!
```

The format is: `/remind YYYY-MM-DD HH:MM Your message here`

**Open web interface:**
```
/web
```

### Setting Reminders via Web Interface

1. Open your browser and go to `http://localhost:8000`
2. You'll see a form to set reminders
3. First, get your Chat ID:
   - Send `/chatid` to your bot on Telegram
   - Copy the Chat ID from the bot's response
4. Fill in the web form:
   - Enter your reminder message
   - Select the date
   - Select the time
   - Paste your Chat ID
5. Click "Set Reminder"

The web interface will show all your reminders and their status.

### Getting Your Chat ID

If you need your Chat ID for the web interface, you have several options:

**Option 1: Use your bot (easiest)**
- Send `/chatid` to your bot
- It will reply with your Chat ID and User ID

**Option 2: Use @userinfobot**
- Search for `@userinfobot` on Telegram
- Start a conversation
- It will send you your user information including Chat ID

**Option 3: Use @getidsbot**
- Search for `@getidsbot` on Telegram
- Start a conversation
- It will display your IDs

## How It Works

1. When you set a reminder, it's stored in a SQLite database (`reminders.db` - created automatically)
2. A background scheduler runs continuously and checks for due reminders every minute
3. When a reminder's scheduled time arrives, the bot automatically sends you a message on Telegram
4. Reminders are marked as sent to prevent duplicate notifications

## API Endpoints

The application provides these endpoints:

- `GET /` - Web interface (homepage)
- `POST /api/set-reminder` - Create a new reminder (used by web form)
- `POST /api/webhook` - Telegram webhook endpoint (for production deployments)
- `GET /api/reminders/{user_id}` - Get all reminders for a specific user

## Project Structure

```
Telegram-Bot/
├── main.py              # Main FastAPI application
├── templates/
│   └── index.html       # Web interface HTML
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (you create this)
├── reminders.db         # SQLite database (auto-created on first run)
├── .gitignore          # Git ignore rules
└── README.md           # This file
```

## Troubleshooting

**Bot doesn't respond to messages:**
- Make sure the server is running (`python main.py`)
- Check that your `.env` file has the correct bot token
- Verify the token is correct by testing it with BotFather

**Can't find the bot on Telegram:**
- Make sure you're searching for the exact username (including the @ symbol)
- Check that you completed the bot creation process with BotFather

**Web interface doesn't load:**
- Make sure the server is running
- Check that port 8000 is not being used by another application
- Try accessing `http://localhost:8000` in your browser

**Reminders not being sent:**
- Make sure the server is still running (it needs to run continuously)
- Check that the reminder date/time is in the future
- Verify your Chat ID is correct

## Production Deployment

For production use, consider:

1. **Use a proper web server**: Instead of running `python main.py`, use a production ASGI server like Gunicorn with Uvicorn workers
2. **Set up webhooks**: For better performance, configure Telegram webhooks instead of polling
3. **Use a production database**: Consider PostgreSQL instead of SQLite for better reliability
4. **Environment variables**: Set `WEB_APP_URL` to your actual domain (e.g., `https://yourdomain.com`)
5. **Use a process manager**: Use systemd, PM2, or similar to keep the bot running

## Notes

- The scheduler checks for reminders every minute, so there may be up to a 1-minute delay
- Reminders must be set for future dates/times
- The database is automatically created when you first run the application
- Keep your `.env` file secure and never share your bot token

## Support

If you have questions or encounter any problems, please raise an issue on the GitHub repository.

Kind regards,  
Goga  