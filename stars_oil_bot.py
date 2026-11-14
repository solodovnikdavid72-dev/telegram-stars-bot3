import logging
import random
import string
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, ConversationHandler
)

# ====================== НАСТРОЙКИ ======================
BOT_TOKEN = "9068472774:AAF2VoI-3XhQV-MmddW0cSQzWR6JrXmk9aU"
ADMIN_ID = None

STAR_PRICE = 1.65
OIL_PRICE = 4500
# =======================================================

WAITING_CONTACT, WAITING_CODE = range(2)

users = {}
pending_codes = {}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def generate_code(length=6):
    return "".join(random.choices(string.digits, k=length))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    if user_id in users and users[user_id].get("verified"):
        await show_main_menu(update, context)
        return ConversationHandler.END

    keyboard = [[KeyboardButton("📱 Поделиться номером телефона", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    await update.message.reply_text(
        f"Привет, {user.first_name}!\n\n"
        "Для регистрации в магазине звёзд и нефти нужно подтвердить номер телефона.\n\n"
        "Нажми кнопку ниже и разреши отправку контакта:",
        reply_markup=reply_markup
    )
    return WAITING_CONTACT


async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    user_id = update.effective_user.id

    if contact.user_id != user_id:
        await update.message.reply_text("Пожалуйста, отправь свой собственный номер.")
        return WAITING_CONTACT

    phone = contact.phone_number
    code = generate_code()

    users[user_id] = {
        "phone": phone,
        "verified": False,
        "code": code,
        "username": update.effective_user.username,
        "full_name": update.effective_user.full_name
    }
    pending_codes[user_id] = code

    await update.message.reply_text(
        f"✅ Номер получен: `{phone}`\n\n"
        f"Твой код подтверждения: **{code}**\n\n"
        "Введи этот код в чат:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["/cancel"]], resize_keyboard=True)
    )
    return WAITING_CODE


async def code_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_id not in pending_codes:
        await update.message.reply_text("Сначала отправь номер телефона. Нажми /start")
        return ConversationHandler.END

    if text == pending_codes[user_id]:
        users[user_id]["verified"] = True
        del pending_codes[user_id]

        await update.message.reply_text(
            "🎉 Регистрация успешно завершена!\n"
            "Теперь ты можешь покупать звёзды и нефть.",
            reply_markup=ReplyKeyboardMarkup([["🏠 Главное меню"]], resize_keyboard=True)
        )
        await show_main_menu(update, context)
        return ConversationHandler.END
    else:
        await update.message.reply_text("❌ Неверный код. Попробуй ещё раз или нажми /start")
        return WAITING_CODE


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⭐ Купить Telegram Stars", callback_data="buy_stars")],
        [InlineKeyboardButton("🛢 Купить нефть", callback_data="buy_oil")],
        [InlineKeyboardButton("👤 Мой профиль", callback_data="profile")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "🛒 **Магазин Stars & Oil**\n\n"
        f"⭐ Telegram Stars — {STAR_PRICE} ₽ за 1 шт.\n"
        f"🛢 Нефть — {OIL_PRICE} ₽ за 1 баррель\n\n"
        "Выбери товар:"
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if user_id not in users or not users[user_id].get("verified"):
        await query.edit_message_text("Сначала пройди регистрацию: /start")
        return

    if data == "buy_stars":
        keyboard = [
            [InlineKeyboardButton("50 ⭐ — 82.5 ₽", callback_data="stars_50")],
            [InlineKeyboardButton("100 ⭐ — 165 ₽", callback_data="stars_100")],
            [InlineKeyboardButton("500 ⭐ — 825 ₽", callback_data="stars_500")],
            [InlineKeyboardButton("1000 ⭐ — 1650 ₽", callback_data="stars_1000")],
            [InlineKeyboardButton("« Назад", callback_data="back_menu")]
        ]
        await query.edit_message_text(
            "Выбери пакет Telegram Stars:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "buy_oil":
        keyboard = [
            [InlineKeyboardButton("1 баррель — 4500 ₽", callback_data="oil_1")],
            [InlineKeyboardButton("5 баррелей — 22000 ₽", callback_data="oil_5")],
            [InlineKeyboardButton("10 баррелей — 42000 ₽", callback_data="oil_10")],
            [InlineKeyboardButton("« Назад", callback_data="back_menu")]
        ]
        await query.edit_message_text(
            "Выбери количество нефти:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("stars_") or data.startswith("oil_"):
        product = "звёзды" if data.startswith("stars_") else "нефть"
        amount = data.split("_")[1]
        await query.edit_message_text(
            f"✅ Заказ на {product} ({amount}) принят!\n\n"
            "В демо-версии оплата ещё не подключена.\n"
            "Напиши администратору для завершения покупки.\n\n"
            "Для возврата в меню нажми /start"
        )

    elif data == "profile":
        u = users[user_id]
        await query.edit_message_text(
            f"👤 **Твой профиль**\n\n"
            f"Имя: {u.get('full_name')}\n"
            f"Username: @{u.get('username') or 'нет'}\n"
            f"Телефон: `{u.get('phone')}`\n"
            f"Статус: ✅ Зарегистрирован",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Назад", callback_data="back_menu")]])
        )

    elif data == "help":
        await query.edit_message_text(
            "ℹ️ **Помощь**\n\n"
            "Бот продаёт Telegram Stars и нефть.\n"
            "После регистрации выбирай товар и оформляй заказ.\n\n"
            "По вопросам пиши администратору.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("« Назад", callback_data="back_menu")]])
        )

    elif data == "back_menu":
        await show_main_menu(update, context)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Регистрация отменена. Нажми /start чтобы начать заново.")
    return ConversationHandler.END


async def main_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users or not users[user_id].get("verified"):
        await update.message.reply_text("Сначала пройди регистрацию: /start")
        return
    await show_main_menu(update, context)


def main():
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WAITING_CONTACT: [MessageHandler(filters.CONTACT, contact_handler)],
            WAITING_CODE: [MessageHandler(filters.TEXT & \~filters.COMMAND, code_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CommandHandler("menu", main_menu_command))
    application.add_handler(MessageHandler(filters.Regex("^🏠 Главное меню$"), main_menu_command))

    print("✅ Бот запущен и работает...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
