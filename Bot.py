from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from ping import Ping
from config import TOKEN as TINKOFF_TOKEN, COMPANIES
import requests
from datetime import datetime

BOT_TOKEN = "8922841684:AAF3K87819eDFYsUfvWsIUTugD8shFk7imE"
MAX_SLOTS = 3

headers = {
    "Authorization": f"Bearer {TINKOFF_TOKEN}",
    "Content-Type": "application/json"
}

user_pings = {}
user_state = {}
figi_cache = {}


def get_figi(ticker):
    if ticker in figi_cache:
        return figi_cache[ticker]
    
    try:
        resp = requests.post(
            "https://invest-public-api.tinkoff.ru/rest/tinkoff.public.invest.api.contract.v1.InstrumentsService/FindInstrument",
            headers=headers, json={"query": ticker}, timeout=5
        )
        instruments = resp.json().get("instruments", [])
        for inst in instruments:
            if inst.get("instrumentType") == "share" and inst.get("apiTradeAvailableFlag"):
                figi_cache[ticker] = inst["figi"]
                return inst["figi"]
        for inst in instruments:
            if inst.get("instrumentType") == "share" and inst.get("classCode") == "TQBR":
                figi_cache[ticker] = inst["figi"]
                return inst["figi"]
    except:
        pass
    return None


def get_price(ticker):
    figi = get_figi(ticker)
    if not figi:
        return None
    
    try:
        resp = requests.post(
            "https://invest-public-api.tinkoff.ru/rest/tinkoff.public.invest.api.contract.v1.MarketDataService/GetLastPrices",
            headers=headers, json={"figi": [figi]}, timeout=5
        )
        data = resp.json()
        last_prices = data.get("lastPrices", [])
        if last_prices and last_prices[0].get("price"):
            p = last_prices[0]["price"]
            return float(p["units"]) + float(p["nano"]) / 1e9
        return None
    except:
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_pings.setdefault(user_id, [])
    
    slots_taken = len(user_pings[user_id])
    text = f"📊 *Биржевой трекер*\nСлотов занято: {slots_taken}/{MAX_SLOTS}"
    
    keyboard = []
    if slots_taken < MAX_SLOTS:
        keyboard.append([InlineKeyboardButton("➕ Добавить пинг", callback_data="add_ping")])
    if user_pings[user_id]:
        keyboard.append([InlineKeyboardButton("🗑 Сбросить всё", callback_data="reset_all")])
    
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except:
        pass
    
    user_id = query.from_user.id
    user_pings.setdefault(user_id, [])
    
    if query.data == "add_ping":
        if len(user_pings[user_id]) >= MAX_SLOTS:
            await query.edit_message_text("❌ Максимум 3 пинга. /start")
            return
        
        keyboard = []
        for num, c in COMPANIES.items():
            if num not in [p["num"] for p in user_pings[user_id]]:
                keyboard.append([InlineKeyboardButton(f"{c['ticker']} — {c['name']}", callback_data=f"c_{num}")])
        keyboard.append([InlineKeyboardButton("« Назад", callback_data="back")])
        await query.edit_message_text("Выберите компанию:", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data.startswith("c_"):
        num = int(query.data.split("_")[1])
        company = COMPANIES[num]
        user_state[user_id] = {"num": num, "company": company}
        
        price = get_price(company["ticker"])
        price_str = f"{price:.2f} ₽" if price else "загружается..."
        
        keyboard = [
            [InlineKeyboardButton("🔻 Ниже", callback_data="d_below"),
             InlineKeyboardButton("🔺 Выше", callback_data="d_above")],
            [InlineKeyboardButton("« Назад", callback_data="add_ping")]
        ]
        await query.edit_message_text(
            f"*{company['name']}* — сейчас {price_str}\nНаправление пинга:",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif query.data.startswith("d_"):
        direction = query.data.split("_")[1]
        user_state[user_id]["direction"] = direction
        d_word = "НИЖЕ" if direction == "below" else "ВЫШЕ"
        await query.edit_message_text(f"Введите цену для пинга ({d_word}):")
    
    elif query.data == "reset_all":
        user_pings[user_id] = []
        user_state.pop(user_id, None)
        await query.edit_message_text("🔄 Сброшено. /start")
    
    elif query.data == "back":
        slots_taken = len(user_pings[user_id])
        text = f"📊 *Биржевой трекер*\nСлотов: {slots_taken}/{MAX_SLOTS}"
        keyboard = []
        if slots_taken < MAX_SLOTS:
            keyboard.append([InlineKeyboardButton("➕ Добавить пинг", callback_data="add_ping")])
        if user_pings[user_id]:
            keyboard.append([InlineKeyboardButton("🗑 Сбросить всё", callback_data="reset_all")])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if user_id in user_state and "direction" in user_state[user_id]:
        try:
            target = float(text.replace(",", "."))
        except ValueError:
            await update.message.reply_text("Введите число!")
            return
        
        state = user_state.pop(user_id)
        company = state["company"]
        direction = state["direction"]
        
        ping = Ping(company["ticker"], company["name"], target, direction)
        user_pings[user_id].append({"num": state["num"], "company": company, "ping": ping})
        
        d = "НИЖЕ" if direction == "below" else "ВЫШЕ"
        await update.message.reply_text(
            f"✅ {company['ticker']} — пинг {d} {target:.2f} ₽\n"
            f"Слотов: {len(user_pings[user_id])}/{MAX_SLOTS}\n/start — меню"
        )
    else:
        await update.message.reply_text("/start для меню.")


async def check_pings(context: ContextTypes.DEFAULT_TYPE):
    if not user_pings:
        return
    
    all_tickers = set()
    for pings_list in user_pings.values():
        for item in pings_list:
            all_tickers.add(item["company"]["ticker"])
    
    prices = {}
    for ticker in all_tickers:
        price = get_price(ticker)
        if price:
            prices[ticker] = price
    
    for user_id, pings_list in list(user_pings.items()):
        to_remove = []
        for item in pings_list:
            ticker = item["company"]["ticker"]
            price = prices.get(ticker)
            
            if price and item["ping"].update(price):
                now = datetime.now().strftime("%H:%M:%S")
                try:
                    await context.bot.send_message(user_id, f"[{now}] {item['ping'].get_alert()}")
                except:
                    pass
                to_remove.append(item)
        
        for item in to_remove:
            pings_list.remove(item)


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.job_queue.run_repeating(check_pings, interval=10, first=3)
    print("Бот запущен!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
