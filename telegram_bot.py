import asyncio
import sys

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from groq import Groq

# Config
GROQ_KEY = "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"  # Groq key của mày
TELEGRAM_TOKEN = "8801419933:AAG7ayi-f7i2mnVvAnqGCFdmFnAsAPDCAR0"       # Token từ BotFather
client = Groq(api_key=GROQ_KEY)

# Lưu lịch sử từng user
histories = {}

# Lệnh /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Chào mày! Tao là AI assistant 🤖\n"
        "Nhắn gì đi, tao trả lời liền!\n"
        "Gõ /reset để xóa lịch sử chat."
    )

# Lệnh /reset
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    histories[user_id] = []
    await update.message.reply_text("Đã xóa lịch sử chat! Bắt đầu lại nhé 🔄")

# Xử lý tin nhắn
async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # Khởi tạo lịch sử nếu chưa có
    if user_id not in histories:
        histories[user_id] = []

    # Thêm tin nhắn user vào lịch sử
    histories[user_id].append({"role": "user", "content": text})

    # Giới hạn 20 tin nhắn gần nhất tránh tốn token
    if len(histories[user_id]) > 20:
        histories[user_id] = histories[user_id][-20:]

    # Gọi AI
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Mày là trợ lý AI thông minh, trả lời bằng tiếng Việt, ngắn gọn và hữu ích."},
                *histories[user_id]
            ],
            max_tokens=1024
        )
        reply_text = response.choices[0].message.content
        histories[user_id].append({"role": "assistant", "content": reply_text})

    except Exception as e:
        reply_text = f"Lỗi rồi mày ơi: {str(e)}"

    await update.message.reply_text(reply_text)

# Chạy bot
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("reset", reset))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))

print("Bot đang chạy... Bấm Ctrl+C để dừng")
app.run_polling()
