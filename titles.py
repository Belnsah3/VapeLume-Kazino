import logging
from datetime import datetime, timedelta
from telegram import Update, ChatAdministratorRights
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from database import get_user_balance, update_user_balance, add_temp_title, get_expired_titles, remove_temp_title, get_bound_supergroup_id

async def check_supergroup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Проверяет, что команда вызвана в привязанной супергруппе.
    Возвращает True, если проверка пройдена, иначе отправляет сообщение об ошибке и возвращает False.
    """
    from database import get_bound_supergroup_id
    
    chat_id = update.effective_chat.id
    bound_supergroup_id = get_bound_supergroup_id()
    
    # Проверяем, что чат - это привязанная супергруппа
    if update.effective_chat.type not in ['group', 'supergroup'] or chat_id != bound_supergroup_id:
        await update.message.reply_text('❌ Эта команда может быть использована только в привязанной супергруппе.')
        return False
    
    return True

# Константы с титулами их параметрами
PERMANENT_TITLES = {
    'Босс': 50000,
    'Король': 25000,
    'Президент': 15000,
    'Мэр': 10000,
    'Бургомистр': 5000,
    'Владыка лудомани': 30000
}

TEMPORARY_TITLES = {
    'Титул на 1 день': {'price': 1000, 'duration_days': 1},
    'Титул на 3 дня': {'price': 2500, 'duration_days': 3},
    'Титул на 7 дней': {'price': 5000, 'duration_days': 7},
    'Титул на 30 дней': {'price': 15000, 'duration_days': 30}
}

async def buytitle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /buytitle для покупки пожизненного титула.
    """
    if not await check_supergroup(update, context):
        return
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Проверяем, указано ли название титула
    if not context.args:
        await update.message.reply_text('❌ Пожалуйста, укажите название титула.\nПример: /buytitle Босс')
        return
    
    title = ' '.join(context.args)
    
    # Проверяем, существует ли титул в списке пожизненных
    if title not in PERMANENT_TITLES:
        available_titles = ', '.join(PERMANENT_TITLES.keys())
        await update.message.reply_text(f'❌ Такой титул не существует.\nДоступные титулы: {available_titles}')
        return
    
    # Проверяем баланс пользователя
    price = PERMANENT_TITLES[title]
    balance = get_user_balance(user_id)
    
    if balance < price:
        await update.message.reply_text(f'❌ Недостаточно средств. Титул "{title}" стоит {price} LumeCoin, а у вас {balance} LumeCoin.')
        return
    
    # Списываем средства
    update_user_balance(user_id, -price)
    
    try:
        # Проверяем, является ли пользователь уже администратором
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        is_already_admin = chat_member.status in ['administrator', 'creator']
        
        # Если пользователь уже администратор, сначала снимаем права
        if is_already_admin:
            await context.bot.promote_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                is_anonymous=False,
                can_manage_chat=False,
                can_delete_messages=False,
                can_manage_video_chats=False,
                can_restrict_members=False,
                can_promote_members=False,
                can_change_info=False,
                can_invite_users=False,
                can_post_messages=False,
                can_edit_messages=False,
                can_pin_messages=False,
                can_post_stories=False,
                can_edit_stories=False,
                can_delete_stories=False,
                can_manage_topics=False
            )
        
        # Назначаем пользователя администратором с пустыми правами
        await context.bot.promote_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            is_anonymous=False,
            can_manage_chat=False,
            can_delete_messages=False,
            can_manage_video_chats=False,
            can_restrict_members=False,
            can_promote_members=False,
            can_change_info=False,
            can_invite_users=False,
            can_post_messages=False,
            can_edit_messages=False,
            can_pin_messages=False,
            can_post_stories=False,
            can_edit_stories=False,
            can_delete_stories=False,
            can_manage_topics=False
        )
        
        # Устанавливаем кастомный титул
        await context.bot.set_chat_administrator_custom_title(
            chat_id=chat_id,
            user_id=user_id,
            custom_title=title
        )
        
        await update.message.reply_text(f'🎉 Поздравляем! Вы купили титул "{title}".')
        
    except TelegramError as e:
        logging.error(f'Ошибка при установке титула: {e}')
        await update.message.reply_text('❌ Произошла ошибка при установке титула. Возможно, у бота недостаточно прав.')


async def renttitle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /renttitle для аренды временного титула.
    """
    if not await check_supergroup(update, context):
        return
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Проверяем, указано ли название титула
    if not context.args:
        await update.message.reply_text('❌ Пожалуйста, укажите название титула.\nПример: /renttitle Титул на 1 день')
        return
    
    title = ' '.join(context.args)
    
    # Проверяем, существует ли титул в списке временных
    if title not in TEMPORARY_TITLES:
        available_titles = ', '.join(TEMPORARY_TITLES.keys())
        await update.message.reply_text(f'❌ Такой временный титул не существует.\nДоступные титулы: {available_titles}')
        return
    
    # Получаем параметры титула
    title_info = TEMPORARY_TITLES[title]
    price = title_info['price']
    duration_days = title_info['duration_days']
    
    # Проверяем баланс пользователя
    balance = get_user_balance(user_id)
    
    if balance < price:
        await update.message.reply_text(f'❌ Недостаточно средств. Аренда "{title}" стоит {price} LumeCoin, а у вас {balance} LumeCoin.')
        return
    
    # Списываем средства
    update_user_balance(user_id, -price)
    
    try:
        # Проверяем, является ли пользователь уже администратором
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        is_already_admin = chat_member.status in ['administrator', 'creator']
        
        # Если пользователь уже администратор, сначала снимаем права
        if is_already_admin:
            await context.bot.promote_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                is_anonymous=False,
                can_manage_chat=False,
                can_delete_messages=False,
                can_manage_video_chats=False,
                can_restrict_members=False,
                can_promote_members=False,
                can_change_info=False,
                can_invite_users=False,
                can_post_messages=False,
                can_edit_messages=False,
                can_pin_messages=False,
                can_post_stories=False,
                can_edit_stories=False,
                can_delete_stories=False,
                can_manage_topics=False
            )
        
        # Назначаем пользователя администратором с пустыми правами
        await context.bot.promote_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            is_anonymous=False,
            can_manage_chat=False,
            can_delete_messages=False,
            can_manage_video_chats=False,
            can_restrict_members=False,
            can_promote_members=False,
            can_change_info=False,
            can_invite_users=False,
            can_post_messages=False,
            can_edit_messages=False,
            can_pin_messages=False,
            can_post_stories=False,
            can_edit_stories=False,
            can_delete_stories=False,
            can_manage_topics=False
        )
        
        # Устанавливаем кастомный титул
        await context.bot.set_chat_administrator_custom_title(
            chat_id=chat_id,
            user_id=user_id,
            custom_title=title
        )
        
        # Рассчитываем дату истечения срока
        expires_at = datetime.now() + timedelta(days=duration_days)
        
        # Сохраняем информацию о временном титуле
        add_temp_title(user_id, chat_id, title, expires_at)
        
        await update.message.reply_text(f'🎉 Поздравляем! Вы арендовали титул "{title}" на {duration_days} дней.')
        
    except TelegramError as e:
        logging.error(f'Ошибка при установке временного титула: {e}')
        await update.message.reply_text('❌ Произошла ошибка при установке титула. Возможно, у бота недостаточно прав.')


async def check_expired_titles(context: ContextTypes.DEFAULT_TYPE):
    """
    Фоновая задача для проверки и снятия истёкших титулов.
    """
    # Получаем привязанный чат из базы данных
    bound_chat_id = get_bound_supergroup_id()
    if not bound_chat_id:
        # Если чат не привязан, завершаем выполнение
        return
    
    # Получаем список истёкших титулов
    expired_titles = get_expired_titles()
    
    for user_id, chat_id in expired_titles:
        try:
            # Снимаем все права и возвращаем пользователя в статус обычного участника
            await context.bot.promote_chat_member(
                chat_id=bound_chat_id,
                user_id=user_id,
                # Устанавливаем все права как False для снятия администраторских прав
                is_anonymous=False,
                can_manage_chat=False,
                can_delete_messages=False,
                can_manage_video_chats=False,
                can_restrict_members=False,
                can_promote_members=False,
                can_change_info=False,
                can_invite_users=False,
                can_post_messages=False,
                can_edit_messages=False,
                can_pin_messages=False,
                can_post_stories=False,
                can_edit_stories=False,
                can_delete_stories=False,
                can_manage_topics=False
            )
            
            # Удаляем запись о временном титуле из БД
            remove_temp_title(user_id, chat_id)
            
            # Опционально: отправляем пользователю уведомление в ЛС
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text='⏰ Срок действия вашего временного титула истёк. Вы больше не являетесь администратором группы.'
                )
            except Exception:
                # Игнорируем ошибки при отправке уведомления (например, если пользователь заблокировал бота)
                pass
                
        except TelegramError as e:
            # Обрабатываем возможные ошибки (например, если бот был разжалован или пользователь покинул чат)
            logging.error(f'Ошибка при снятии титула у пользователя {user_id}: {e}')
            continue  # Продолжаем с другими пользователями


async def titles_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /titles для просмотра доступных титулов.
    """
    # Формируем сообщение с пожизненными титулами
    permanent_titles_text = "*Пожизненные титулы:*\n"
    for title, price in PERMANENT_TITLES.items():
        permanent_titles_text += f"• *{title}*: {price} LumeCoin\n"
    
    # Формируем сообщение с временными титулами
    temporary_titles_text = "\n*Временные титулы:*\n"
    for title, info in TEMPORARY_TITLES.items():
        temporary_titles_text += f"• *{title}*: {info['price']} LumeCoin (на {info['duration_days']} дней)\n"
    
    # Объединяем оба списка
    full_message = permanent_titles_text + temporary_titles_text
    
    # Отправляем сообщение
    await update.message.reply_text(full_message, parse_mode='Markdown')