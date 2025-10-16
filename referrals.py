from telegram.ext import ContextTypes, CommandHandler
from telegram import Update
import database
from games import update_user_balance


async def ref_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /ref - генерирует реферальную ссылку и показывает статистику
    """
    user_id = update.effective_user.id
    
    # Получаем количество приглашенных пользователей
    referral_count = database.get_referral_count(user_id)
    
    # Генерируем реферальную ссылку
    bot_username = context.bot.username
    referral_link = f'https://t.me/{bot_username}?start=ref{user_id}'
    
    message = (
        f'Ваша реферальная ссылка:\n'
        f'{referral_link}\n\n'
        f'Вы пригласили: {referral_count} пользователей'
    )
    
    await update.message.reply_text(message)


ref_handler = CommandHandler('ref', ref_command)