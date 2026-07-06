import asyncio
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from groq import Groq

GROQ_KEY = os.environ.get("GROQ_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

client = Groq(api_key=GROQ_KEY)
histories = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Chào mày! Tao là AI assistant 🤖\n"
        "Nhắn gì đi, tao trả lời liền!\n"
        "Gõ /reset để xóa lịch sử chat."
    )

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    histories[user_id] = []
    await update.message.reply_text("Đã xóa lịch sử! Bắt đầu lại nhé 🔄")

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id not in histories:
        histories[user_id] = []

    histories[user_id].append({"role": "user", "content": text})

    if len(histories[user_id]) > 20:
        histories[user_id] = histories[user_id][-20:]

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Mày là trợ lý AI, trả lời tiếng Việt, ngắn gọn và hữu ích."},
                *histories[user_id]
            ],
            max_tokens=1024
        )
        reply_text = response.choices[0].message.content
        histories[user_id].append({"role": "assistant", "content": reply_text})
    except Exception as e:
        reply_text = f"Lỗi rồi: {str(e)}"

    await update.message.reply_text(reply_text)

async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))
    print("Bot đang chạy 24/7...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
