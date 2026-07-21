from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = "8922841684:AAF3K87819eDFYsUfvWsIUTugD8shFk7imE"
PROXY = "socks5://m552vY:rYuUFs@217.29.63.103:12550"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот работает!")

def main():
    app = Application.builder().token(BOT_TOKEN).proxy(PROXY).get_updates_proxy(PROXY).build()
    app.add_handler(CommandHandler("start", start))
    print("Пробую подключиться...")
    app.run_polling()

if __name__ == "__main__":
    main()