from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from database import get_user_balance, update_user_balance, get_user_discount_tier, set_user_discount_tier, get_available_vpn_code, add_vpn_codes
import logging

def get_user_id(update: Update) -> int:
    """Получение ID пользователя из обновления"""
    return update.effective_user.id

logger = logging.getLogger(__name__)

def private_only(func):
    """Декоратор для проверки, что команда вызвана в личном чате"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.type != 'private':
            await update.message.reply_text('❌ Эта команда доступна только в личных сообщениях.')
            return
        return await func(update, context)
    return wrapper

@private_only
async def shop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для открытия магазина скидок"""
    keyboard = [
        [InlineKeyboardButton('5% скидка - 5000 LumeCoin', callback_data='discount_5')],
        [InlineKeyboardButton('10% скидка - 10000 LumeCoin', callback_data='discount_10')],
        [InlineKeyboardButton('20% скидка - 20000 LumeCoin', callback_data='discount_20')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('🛒 Выберите уровень скидки:', reply_markup=reply_markup)

async def discount_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки покупки скидки"""
    query = update.callback_query
    await query.answer()

    user_id = get_user_id(update)
    callback_data = query.data

    # Определяем уровень скидки и стоимость
    discount_mapping = {
        'discount_5': (5, 5000),
        'discount_10': (10, 10000),
        'discount_20': (20, 20000)
    }

    if callback_data not in discount_mapping:
        await query.edit_message_text('❌ Неверная команда.')
        return

    discount_tier, cost = discount_mapping[callback_data]

    # Проверяем баланс пользователя
    current_balance = get_user_balance(user_id)
    if current_balance < cost:
        await query.edit_message_text(f'❌ Недостаточно средств. Ваш баланс: {current_balance} LumeCoin')
        return

    # Списываем средства и устанавливаем уровень скидки
    update_user_balance(user_id, current_balance - cost)
    set_user_discount_tier(user_id, discount_tier)

    await query.edit_message_text(f'✅ Вы приобрели скидку {discount_tier}%. Средства списаны.')

@private_only
async def vpn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для покупки VPN-промокодов"""
    keyboard = [
        [InlineKeyboardButton('1 неделя - 3000 LumeCoin', callback_data='vpn_1w')],
        [InlineKeyboardButton('1 месяц - 10000 LumeCoin', callback_data='vpn_1m')],
        [InlineKeyboardButton('3 месяца - 25000 LumeCoin', callback_data='vpn_3m')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('🛒 Выберите период VPN:', reply_markup=reply_markup)

async def vpn_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки покупки VPN"""
    query = update.callback_query
    await query.answer()

    user_id = get_user_id(update)
    callback_data = query.data

    # Определяем тип VPN и стоимость
    vpn_mapping = {
        'vpn_1w': ('1w', 3000, '1 неделю'),
        'vpn_1m': ('1m', 10000, '1 месяц'),
        'vpn_3m': ('3m', 25000, '3 месяца')
    }

    if callback_data not in vpn_mapping:
        await query.edit_message_text('❌ Неверная команда.')
        return

    vpn_type, cost, period = vpn_mapping[callback_data]

    # Проверяем баланс пользователя
    current_balance = get_user_balance(user_id)
    if current_balance < cost:
        await query.edit_message_text(f'❌ Недостаточно средств. Ваш баланс: {current_balance} LumeCoin')
        return

    # Проверяем наличие доступных промокодов
    vpn_code = get_available_vpn_code(vpn_type)
    if not vpn_code:
        await query.edit_message_text('❌ К сожалению, в данный момент нет доступных промокодов.')
        return

    # Списываем средства
    update_user_balance(user_id, current_balance - cost)

    # Отправляем промокод пользователю
    await query.edit_message_text(f'Ваш промокод на {period}: `{vpn_code}`. Активировать в @NaizekVPN_bot.', parse_mode='Markdown')

# Регистрация хендлеров
def register_handlers(application):
    application.add_handler(CommandHandler('shop', shop_command))
    application.add_handler(CallbackQueryHandler(discount_callback, pattern='^discount_'))
    application.add_handler(CommandHandler('vpn', vpn_command))
    application.add_handler(CallbackQueryHandler(vpn_callback, pattern='^vpn_'))