import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("maska-market")
TOKEN = os.getenv("BOT_TOKEN", "").strip()
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "Daddimix").strip().lstrip("@")
ADMIN_CHAT_ID_RAW = os.getenv("ADMIN_CHAT_ID", "").strip()
ADMIN_CHAT_ID = int(ADMIN_CHAT_ID_RAW) if ADMIN_CHAT_ID_RAW else None

BASE_DIR = Path(getattr(__import__('sys'), '_MEIPASS', Path(__file__).resolve().parent))
try:
    PRODUCTS = json.loads((BASE_DIR / "products.json").read_text(encoding="utf-8"))
except Exception:
    PRODUCTS = [{"id": "demo", "name": "Демо-товар", "description": "Добавьте свои товары в products.json", "price": "Укажите цену"}]

HOME_TEXT = (
    "🎭 <b>MASKA MARKET</b>\n\n"
    "Добро пожаловать в цифровой магазин.\n\n"
    "Выберите раздел ниже ↓"
)


def keyboard(rows):
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=data) for label, data in row] for row in rows])


def home_keyboard():
    return keyboard([
        [("🛍 Купить товар", "catalog")],
        [("◇ Мои покупки", "purchases"), ("▣ Баланс", "balance")],
        [("♡ Акции", "promos"), ("🔗 Наши ссылки", "links")],
        [("▤ Поддержка", "support"), ("ⓘ Информация", "info")],
    ])

async def show(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, markup=None):
    q = update.callback_query
    if q:
        await q.answer()
        try:
            await q.edit_message_text(text, reply_markup=markup, parse_mode="HTML", disable_web_page_preview=True)
        except Exception as exc:
            if "Message is not modified" not in str(exc):
                raise
    elif update.message:
        await update.message.reply_text(text, reply_markup=markup, parse_mode="HTML", disable_web_page_preview=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("waiting_support", None)
    await show(update, context, HOME_TEXT, home_keyboard())

async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data or "home"
    if data == "home":
        context.user_data.pop("waiting_support", None)
        return await show(update, context, HOME_TEXT, home_keyboard())
    if data == "catalog":
        rows = [[(f"🛒 {p['name']} — {p['price']}", f"product:{p['id']}")] for p in PRODUCTS]
        rows.append([("↩ Главное меню", "home")])
        return await show(update, context, "🛍 <b>Каталог товаров</b>\n\nВыберите товар, чтобы посмотреть описание и условия покупки.", keyboard(rows))
    if data.startswith("product:"):
        pid = data.split(":", 1)[1]
        p = next((x for x in PRODUCTS if str(x.get("id")) == pid), None)
        if not p:
            return await show(update, context, "Товар не найден. Обновите каталог и попробуйте снова.", keyboard([[ ("↩ Каталог", "catalog")], [("Главное меню", "home")]]))
        context.user_data["selected_product"] = pid
        text = f"🛍 <b>{p['name']}</b>\n\n{p.get('description', 'Описание пока не добавлено.')}\n\n<b>Цена:</b> {p['price']}\n\nВыдача цифрового товара производится после подтверждения оплаты."
        return await show(update, context, text, keyboard([[ ("💳 Перейти к покупке", f"buy:{pid}")], [("↩ Каталог", "catalog")], [("Главное меню", "home")]]))
    if data.startswith("buy:"):
        pid = data.split(":", 1)[1]
        p = next((x for x in PRODUCTS if str(x.get("id")) == pid), None)
        name = p.get("name", "товар") if p else "товар"
        return await show(update, context, f"💳 <b>Покупка: {name}</b>\n\nАвтоматическая оплата пока не подключена. Не отправляйте деньги до получения реквизитов и подтверждения заказа сотрудником.\n\nДля оформления обратитесь в поддержку: @{SUPPORT_USERNAME}", keyboard([[ ("▤ Поддержка", "support")], [("↩ Каталог", "catalog")], [("Главное меню", "home")]]))
    if data == "purchases":
        return await show(update, context, "◇ <b>Мои покупки</b>\n\nЗдесь будут отображаться ваши оплаченные заказы. В этой версии история покупок ещё не подключена.\n\nЕсли вы уже оплатили заказ, напишите в поддержку и приложите номер заказа или подтверждение оплаты.", keyboard([[ ("▤ Поддержка", "support")], [("↩ Главное меню", "home")]]))
    if data == "balance":
        return await show(update, context, "▣ <b>Баланс</b>\n\nБаланс аккаунта: <b>не подключён</b>. Не переводите средства в расчёте на автоматическое зачисление — платёжная система пока не настроена.\n\nПо вопросам оплаты: @{SUPPORT_USERNAME}", keyboard([[ ("▤ Поддержка", "support")], [("↩ Главное меню", "home")]]))
    if data == "promos":
        return await show(update, context, "🏷 <b>Акции</b>\n\nЕсли у вас есть промокод, введите его в карточке товара или уточните условия у поддержки.\n\nДействующие акции и скидки публикуются здесь после добавления администратором.", keyboard([[ ("🛍 Купить товар", "catalog")], [("▤ Поддержка", "support")], [("↩ Главное меню", "home")]]))
    if data == "links":
        return await show(update, context, f"🔗 <b>Наши ссылки</b>\n\nПоддержка: @{SUPPORT_USERNAME}\n\nОфициальные ссылки магазина будут добавлены администратором. Остерегайтесь поддельных аккаунтов и не передавайте коды входа.", keyboard([[ ("✉ Написать в поддержку", "support")], [("↩ Главное меню", "home")]]))
    if data == "support":
        context.user_data["waiting_support"] = True
        return await show(update, context, f"💬 <b>Поддержка</b>\n\nКонтакт: @{SUPPORT_USERNAME}\n\nНапишите сообщение следующим сообщением — бот передаст его сотруднику, если настроен ADMIN_CHAT_ID. Иначе свяжитесь с оператором напрямую.\n\nДля отмены нажмите «Главное меню».", keyboard([[ ("↩ Главное меню", "home")]]))
    if data == "info":
        return await show(update, context, f"ℹ️ <b>Цифровой магазин</b>\n\n• Товары выдаются автоматически только после подтверждения оплаты, если автоматическая выдача настроена для товара.\n• Банк проверяется сотрудником.\n• Для USDT отправьте TXID после перевода и дождитесь подтверждения сотрудника.\n• Вопросы по заказу: откройте покупку и нажмите «Поддержка».\n\nПоддержка: @{SUPPORT_USERNAME}\n\nВажно: в текущем шаблоне платёжный шлюз и автоматическая выдача не подключены.", keyboard([[ ("🛍 Купить товар", "catalog")], [("▤ Поддержка", "support")], [("↩ Главное меню", "home")]]))
    await show(update, context, HOME_TEXT, home_keyboard())

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if context.user_data.get("waiting_support"):
        message = update.message.text.strip()
        if not message:
            return
        user = update.effective_user
        if ADMIN_CHAT_ID:
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=(f"📩 <b>Сообщение в поддержку MASKA MARKET</b>\n"
                          f"От: {user.full_name} (@{user.username or 'без username'})\n"
                          f"Telegram ID: <code>{user.id}</code>\n\n{message}"),
                    parse_mode="HTML"
                )
                await update.message.reply_text("✅ Сообщение передано сотруднику. Ожидайте ответа.", reply_markup=home_keyboard())
            except Exception:
                log.exception("Failed to send support message")
                await update.message.reply_text(f"Не удалось передать сообщение автоматически. Напишите напрямую: @{SUPPORT_USERNAME}", reply_markup=home_keyboard())
        else:
            await update.message.reply_text(f"Сообщение не отправлено сотруднику: администратор ещё не настроен. Напишите напрямую: @{SUPPORT_USERNAME}", reply_markup=home_keyboard())
        context.user_data.pop("waiting_support", None)
        return
    await update.message.reply_text("Используйте кнопки меню ниже или отправьте /start.", reply_markup=home_keyboard())

async def post_init(app: Application):
    await app.bot.set_my_commands([("start", "Открыть главное меню")])

def main():
    if not TOKEN:
        raise SystemExit("Не задан BOT_TOKEN. Создайте .env по примеру .env.example и добавьте токен от BotFather.")
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    log.info("MASKA MARKET bot started")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
