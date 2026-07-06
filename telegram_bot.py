import asyncio
import os
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from groq import Groq
import pypdf
import io

GROQ_KEY = os.environ.get("GROQ_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

client = Groq(api_key=GROQ_KEY)
histories = {}
MEMORY_FILE = "memory.json"

# Đọc bộ nhớ từ file
def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# Lưu bộ nhớ vào file
def save_memory(data):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Load memory lúc khởi động
memory = load_memory()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    name = update.effective_user.first_name
    
    # Nhớ tên user
    if user_id not in memory:
        memory[user_id] = {"name": name, "notes": []}
        save_memory(memory)
    
    await update.message.reply_text(
        f"Chào {name}! Tao là AI assistant 🤖\n"
        "Nhắn gì đi, tao trả lời liền!\n\n"
        "Lệnh:\n"
        "/reset - Xóa lịch sử chat\n"
        "/remember <nội dung> - Nhờ tao nhớ gì đó\n"
        "/forget - Xóa toàn bộ bộ nhớ\n"
        "📎 Gửi file PDF/TXT để tao đọc và trả lời"
    )

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    histories[user_id] = []
    await update.message.reply_text("Đã xóa lịch sử chat! 🔄")

async def remember(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    note = " ".join(context.args)
    
    if not note:
        await update.message.reply_text("Gõ: /remember <nội dung muốn nhớ>")
        return
    
    if user_id not in memory:
        memory[user_id] = {"notes": []}
    
    memory[user_id]["notes"].append(note)
    save_memory(memory)
    await update.message.reply_text(f"Đã nhớ: {note} ✅")

async def forget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id in memory:
        memory[user_id]["notes"] = []
        save_memory(memory)
    await update.message.reply_text("Đã xóa toàn bộ bộ nhớ! 🗑️")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    doc = update.message.document
    
    # Kiểm tra định dạng file
    if not doc.file_name.endswith(('.pdf', '.txt')):
        await update.message.reply_text("Tao chỉ đọc được file PDF và TXT thôi!")
        return
    
    await update.message.reply_text("Đang đọc file... ⏳")
    
    # Tải file về
    file = await context.bot.get_file(doc.file_id)
    file_bytes = await file.download_as_bytearray()
    
    # Đọc nội dung
    if doc.file_name.endswith('.pdf'):
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        text = "\n".join(page.extract_text() for page in reader.pages)
    else:
        text = file_bytes.decode("utf-8")
    
    # Giới hạn 8000 ký tự tránh tốn token
    if len(text) > 8000:
        text = text[:8000] + "\n...(còn tiếp)"
    
    # Lưu nội dung file vào lịch sử
    if user_id not in histories:
        histories[user_id] = []
    
    histories[user_id].append({
        "role": "user",
        "content": f"Đây là nội dung file '{doc.file_name}':\n{text}\n\nHãy tóm tắt file này cho tao."
    })
    
    # Gọi AI tóm tắt
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
    
    await update.message.reply_text(f"📄 Đã đọc file!\n\n{reply_text}")

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text

    if user_id not in histories:
        histories[user_id] = []

    histories[user_id].append({"role": "user", "content": text})

    if len(histories[user_id]) > 20:
        histories[user_id] = histories[user_id][-20:]

    # Lấy bộ nhớ của user
    user_notes = ""
    if user_id in memory and memory[user_id].get("notes"):
        notes = "\n".join(memory[user_id]["notes"])
        user_notes = f"\nThông tin tao cần nhớ về user:\n{notes}"

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": f"Mày là trợ lý AI, trả lời tiếng Việt, ngắn gọn và hữu ích.{user_notes}"},
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
    app.add_handler(CommandHandler("remember", remember))
    app.add_handler(CommandHandler("forget", forget))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))
    print("Bot đang chạy 24/7...")
    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())