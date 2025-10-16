import os
from functools import wraps
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import Update
from database import initialize_database, get_bound_supergroup_id, set_bound_supergroup_id, get_all_admin_ids, add_admin, remove_admin, get_user_balance, update_user_balance, get_top_users_by_balance, add_vpn_codes, add_referral, get_referrer_id, get_referral_reward_status, mark_referral_reward_as_claimed, get_inactive_users, add_interaction

# Загрузка переменных окружения
from dotenv import load_dotenv
load_dotenv()
from games import roulette, play, russian, jewish, dice, slots
from gamification import xp_handler, profile_handler
from titles import buytitle_command, renttitle_command, check_expired_titles, titles_command
from admin_panel import register_admin_handlers

# Команда для привязки группы (добавлена для корректной работы)
async def bindgroup(update, context):
    """Команда для привязки супергруппы"""
    user_id = update.effective_user.id
    
    # Проверяем, является ли пользователь владельцем
    if user_id != 8415112409:  # OWNER_ID
        return
    
    chat_id = update.effective_chat.id
    
    # Сохраняем ID супергруппы в базу данных
    set_bound_supergroup_id(chat_id)
    
    await update.message.reply_text(f'✅ Супергруппа привязана: {chat_id}')

OWNER_ID = int(os.getenv('OWNER_ID', '8415112409'))


async def help_command(update, context):
    """Команда /help для отображения списка всех команд"""
    help_message = """
📖 Список доступных команд:

💰 <b>Экономика:</b>
• /balance - Проверить баланс
• /top - Топ пользователей по балансу
• /pay - Перевести LumeCoin другому пользователю

🎲 <b>Игры:</b>
• /roulette [ставка] - Рулетка (ставка ≥ 25 LumeCoin, 30% шанс выигрыша)
• /play - Игра в кости (25 LumeCoin, 40% шанс выиграть 40 LumeCoin)
• /russian - Русская рулетка (бесплатно, 35% шанс выиграть 35 LumeCoin)
• /jewish - Еврейская рулетка (бесплатно, 50% шанс выиграть 25 LumeCoin)
• /dice [ставка] - Игра в кости с Telegram-анимацией (ставка 10-100 LumeCoin)
• /slots - Игра в слоты (50 LumeCoin, шанс выигрыша зависит от результата)

🎁 <b>Бонусы и награды:</b>
• /bonus - Ежедневный бонус (раз в 24 часа)
• /case - Открыть кейс (10 LumeCoin, раз в 24 часа)

👤 <b>Профиль и геймификация:</b>
• /profile - Просмотреть свой профиль
• /titles - Просмотреть доступные титулы

🏷 <b>Титулы:</b>
• /buytitle - Купить титул
• /renttitle - Арендовать титул

🔗 <b>Дополнительно:</b>
• /start - Начать взаимодействие с ботом
• /help - Показать это сообщение
"""

    await update.message.reply_text(help_message, parse_mode='HTML')


def owner_only(func):
    """
    Декоратор, который проверяет, является ли автор сообщения владельцем.
    """
    @wraps(func)
    async def wrapper(update, context):
        user_id = update.effective_user.id
        if user_id != OWNER_ID:
            return # Игнорировать команду, если пользователь не является владельцем
        return await func(update, context)
    return wrapper


def is_admin(user_id: int) -> bool:
    """
    Проверяет, является ли пользователь владельцем или есть в списке администраторов.
    """
    if user_id == OWNER_ID:
        return True
    admin_ids = get_all_admin_ids()
    return user_id in admin_ids


def admin_only(func):
    """
    Декоратор, использующий is_admin() для проверки прав.
    """
    @wraps(func)
    async def wrapper(update, context):
        user_id = update.effective_user.id
        if not is_admin(user_id):
            return  # Игнорировать команду, если пользователь не является администратором
        return await func(update, context)
    return wrapper


def group_only(func):
    """
    Декоратор, который проверяет, что команда вызвана в привязанной супергруппе.
    """
    @wraps(func)
    async def wrapper(update, context):
        chat_id = update.effective_chat.id
        bound_supergroup_id = get_bound_supergroup_id()
        
        # Проверяем, что чат - это привязанная супергруппа
        if update.effective_chat.type not in ['group', 'supergroup'] or chat_id != bound_supergroup_id:
            return  # Игнорировать команду, если она вызвана не в привязанной супергруппе
        
        return await func(update, context)
    return wrapper


async def start(update, context):
    """Обновленная команда /start, проверяющая существование пользователя и выводящая баланс"""
    user_id = update.effective_user.id
    
    # Проверяем, есть ли реферальный код в команде
    referrer_id = None
    if context.args and len(context.args) > 0:
        ref_arg = context.args[0]
        if ref_arg.startswith('ref') and ref_arg[3:].isdigit():
            referrer_id = int(ref_arg[3:])
            # Проверяем, что referrer_id не равен user_id (пользователь не может быть реферером сам себе)
            if referrer_id == user_id:
                referrer_id = None
    
    # Проверяем существование пользователя и создаем при необходимости
    balance = get_user_balance(user_id)
    
    # Проверяем, является ли пользователь новым (баланс равен начальному значению)
    is_new_user = balance == 100.0  # Предполагаем, что начальный баланс 100.0
    
    if referrer_id and is_new_user:
        # Проверяем, что пользователь еще не имеет реферера
        existing_referrer = get_referrer_id(user_id)
        if existing_referrer is None:
            # Добавляем запись о реферале
            add_referral(user_id, referrer_id)
            
            # Начисляем бонусы
            update_user_balance(user_id, 200.0)  # +200 LumeCoin новому пользователю
            update_user_balance(referrer_id, 100.0) # +100 LumeCoin пригласившему
            
            # Отправляем приветственное сообщение с упоминанием бонуса
            welcome_message = (
                f'👋 Добро пожаловать в VapeLume Kazino!\n'
                f'💰 Ваш начальный баланс: {get_user_balance(user_id):.1f} LumeCoin\n\n'
                f'🎁 Вы получили 200 LumeCoin за регистрацию по реферальной ссылке!'
            )
            await update.message.reply_text(welcome_message)
            
            # Уведомляем пригласившего о новом реферале
            try:
                await context.bot.send_message(
                    chat_id=referrer_id,
                    text=f'🎉 Пользователь присоединился по вашей реферальной ссылке! Вы получили 100 LumeCoin в награду.'
                )
            except Exception:
                # Игнорируем ошибки при отправке сообщения пригласившему
                pass
        else:
            # Если у пользователя уже есть реферер, просто приветствуем
            welcome_message = f'👋 Добро пожаловать в VapeLume Kazino!\n💰 Ваш баланс: {balance:.1f} LumeCoin'
            await update.message.reply_text(welcome_message)
    else:
        # Обычное приветствие
        welcome_message = f'👋 Добро пожаловать в VapeLume Kazino!\n💰 Ваш начальный баланс: {balance:.1f} LumeCoin'
        await update.message.reply_text(welcome_message)


async def balance(update, context):
    """Команда /balance для проверки баланса пользователя"""
    user_id = update.effective_user.id
    balance = get_user_balance(user_id)
    
    await update.message.reply_text(f'💰 Ваш баланс: {balance:.1f} LumeCoin')


async def top(update, context):
    """Команда /top для вывода топа пользователей по балансу"""
    top_users = get_top_users_by_balance(10)
    
    if not top_users:
        await update.message.reply_text('📊 Рейтинг пользователей пока пуст.')
        return
    
    # Формируем сообщение с рейтингом
    top_message = '🏆 Топ пользователей по балансу:\n\n'
    for i, (user_id, balance) in enumerate(top_users, 1):
        try:
            user = await context.bot.get_chat(user_id)
            username = user.username or user.first_name or f'ID: {user_id}'
        except Exception:
            username = f'ID: {user_id}'
        
        top_message += f'{i}. {username} - {balance:.1f} LumeCoin\n'
    
    await update.message.reply_text(top_message)


@group_only
async def pay(update, context):
    """Команда /pay для перевода LumeCoin другому пользователю"""
    user_id = update.effective_user.id
    
    # Проверяем, является ли команда ответом на сообщение
    if not update.message.reply_to_message:
        await update.message.reply_text('❌ Для перевода средств используйте команду в ответ на сообщение получателя.')
        return
    
    recipient_user_id = update.message.reply_to_message.from_user.id
    
    # Проверяем, что отправитель не пытается перевести себе
    if recipient_user_id == user_id:
        await update.message.reply_text('❌ Нельзя перевести средства самому себе.')
        return
    
    # Парсим сумму из аргументов
    if not context.args or len(context.args) != 1:
        await update.message.reply_text('❌ Укажите сумму перевода: /pay <сумма>')
        return
    
    try:
        amount = float(context.args[0])
        if amount <= 0:
            await update.message.reply_text('❌ Сумма перевода должна быть больше 0.')
            return
    except ValueError:
        await update.message.reply_text('❌ Некорректная сумма. Укажите число: /pay <сумма>')
        return
    
    # Проверяем, достаточно ли средств у отправителя
    sender_balance = get_user_balance(user_id)
    if sender_balance < amount:
        await update.message.reply_text(f'❌ Недостаточно средств для перевода. Ваш баланс: {sender_balance:.1f} LumeCoin')
        return
    
    # Выполняем перевод
    update_user_balance(user_id, -amount)  # Списание у отправителя
    update_user_balance(recipient_user_id, amount) # Зачисление получателю
    
    # Подтверждение перевода
    try:
        recipient_user = await context.bot.get_chat(recipient_user_id)
        recipient_name = recipient_user.username or recipient_user.first_name or f'ID: {recipient_user_id}'
    except Exception:
        recipient_name = f'ID: {recipient_user_id}'
    
    await update.message.reply_text(f'✅ Успешный перевод!\nПереведено {amount:.1f} LumeCoin пользователю {recipient_name}.')


@admin_only
async def give(update, context):
    """Админ-команда /give для начисления LumeCoin пользователю"""
    # Проверяем, является ли команда ответом на сообщение
    if not update.message.reply_to_message:
        await update.message.reply_text('❌ Для начисления используйте команду в ответ на сообщение пользователя.')
        return
    
    recipient_user_id = update.message.reply_to_message.from_user.id
    
    # Парсим сумму из аргументов
    if not context.args or len(context.args) != 1:
        await update.message.reply_text('❌ Укажите сумму для начисления: /give <сумма>')
        return
    
    try:
        amount = float(context.args[0])
        if amount <= 0:
            await update.message.reply_text('❌ Сумма должна быть больше 0.')
            return
    except ValueError:
        await update.message.reply_text('❌ Некорректная сумма. Укажите число: /give <сумма>')
        return
    
    # Начисляем средства
    update_user_balance(recipient_user_id, amount)
    
    # Подтверждение
    try:
        recipient_user = await context.bot.get_chat(recipient_user_id)
        recipient_name = recipient_user.username or recipient_user.first_name or f'ID: {recipient_user_id}'
    except Exception:
        recipient_name = f'ID: {recipient_user_id}'
    
    await update.message.reply_text(f'✅ Администратор начислил {amount:.1f} LumeCoin пользователю {recipient_name}.')


@admin_only
async def getback(update, context):
    """Админ-команда /getback для списания LumeCoin у пользователя"""
    # Проверяем, является ли команда ответом на сообщение
    if not update.message.reply_to_message:
        await update.message.reply_text('❌ Для списания используйте команду в ответ на сообщение пользователя.')
        return
    
    recipient_user_id = update.message.reply_to_message.from_user.id
    
    # Парсим сумму из аргументов
    if not context.args or len(context.args) != 1:
        await update.message.reply_text('❌ Укажите сумму для списания: /getback <сумма>')
        return
    
    try:
        amount = float(context.args[0])
        if amount <= 0:
            await update.message.reply_text('❌ Сумма должна быть больше 0.')
            return
    except ValueError:
        await update.message.reply_text('❌ Некорректная сумма. Укажите число: /getback <сумма>')
        return
    
    # Списание средств (с передачей отрицательного значения)
    update_user_balance(recipient_user_id, -amount)
    
    # Подтверждение
    try:
        recipient_user = await context.bot.get_chat(recipient_user_id)
        recipient_name = recipient_user.username or recipient_user.first_name or f'ID: {recipient_user_id}'
    except Exception:
        recipient_name = f'ID: {recipient_user_id}'
    
    await update.message.reply_text(f'✅ Администратор списал {amount:.1f} LumeCoin у пользователя {recipient_name}.')


@admin_only
async def getbalance(update, context):
    """Админ-команда /getbalance для начисления LumeCoin администратору"""
    user_id = update.effective_user.id
    
    # Парсим сумму из аргументов
    if not context.args or len(context.args) != 1:
        await update.message.reply_text('❌ Укажите сумму для начисления: /getbalance <сумма>')
        return
    
    try:
        amount = float(context.args[0])
        if amount <= 0:
            await update.message.reply_text('❌ Сумма должна быть больше 0.')
            return
    except ValueError:
        await update.message.reply_text('❌ Некорректная сумма. Укажите число: /getbalance <сумма>')
        return
    
    # Начисляем средства администратору
    update_user_balance(user_id, amount)
    
    await update.message.reply_text(f'✅ Администратор получил {amount:.1f} LumeCoin.')


@owner_only
async def addadmin(update, context):
    """
    Команда для добавления администратора.
    """
    # Получаем user_id из текста команды или из reply
    user_id = None
    
    # Проверяем, есть ли текст после команды
    if context.args:
        try:
            user_id = int(context.args[0])
        except ValueError:
            # Если не число, возможно это @username
            username = context.args[0].lstrip('@')
            # Для получения user_id по username нужно получить информацию о пользователе через API
            # Но в текущем подходе мы не можем получить user_id по username напрямую без дополнительного запроса
            # Поэтому будем использовать только числовой ID
            pass
    elif update.message.reply_to_message:
        # Если команда используется в ответ на сообщение
        user_id = update.message.reply_to_message.from_user.id
    
    if not user_id:
        await update.message.reply_text('❌ Укажите ID пользователя или используйте команду в ответ на сообщение пользователя.')
        return
    
    # Добавляем администратора
    add_admin(user_id)
    await update.message.reply_text(f'✅ Пользователь {user_id} добавлен в администраторы.')


@owner_only
async def deladmin(update, context):
    """
    Команда для удаления администратора.
    """
    # Получаем user_id из текста команды или из reply
    user_id = None
    
    # Проверяем, есть ли текст после команды
    if context.args:
        try:
            user_id = int(context.args[0])
        except ValueError:
            # Если не число, возможно это @username
            username = context.args[0].lstrip('@')
            # Для получения user_id по username нужно получить информацию о пользователе через API
            # Но в текущем подходе мы не можем получить user_id по username напрямую без дополнительного запроса
            # Поэтому будем использовать только числовой ID
            pass
    elif update.message.reply_to_message:
        # Если команда используется в ответ на сообщение
        user_id = update.message.reply_to_message.from_user.id
    
    if not user_id:
        await update.message.reply_text('❌ Укажите ID пользователя или используйте команду в ответ на сообщение пользователя.')
        return
    
    # Удаляем администратора
    remove_admin(user_id)
    await update.message.reply_text(f'✅ Пользователь {user_id} удален из администраторов.')


@owner_only
async def listadmins(update, context):
    """
    Команда для вывода списка администраторов.
    """
    admin_ids = get_all_admin_ids()
    
    if not admin_ids:
        await update.message.reply_text('📋 Список администраторов пуст.')
        return
    
    # Формируем читаемый список администраторов
    admin_list = '\n'.join([f'• {admin_id}' for admin_id in admin_ids])
    await update.message.reply_text(f'📋 Список администраторов:\n{admin_list}')


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех текстовых сообщений для отслеживания активности"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Обновляем время последнего взаимодействия пользователя
    add_interaction(user_id)
    
    # Если сообщение отправлено в группу, также обновляем время взаимодействия в группе
    if update.effective_chat.type in ['group', 'supergroup']:
        # Добавляем запись о взаимодействии в группе
        pass # Реализация зависит от структуры БД


def send_reminders(context):
    """Отправляет напоминания неактивным пользователям"""
    inactive_users = get_inactive_users(days=3)
    
    for user_id in inactive_users:
        try:
            context.bot.send_message(
                chat_id=user_id,
                text="Мы скучаем! Возвращайся в чат, чтобы получить бонус!"
            )
        except Exception as e:
            print(f"Не удалось отправить напоминание пользователю {user_id}: {e}")


def main():
    """Основная функция запуска бота"""
    # Инициализация базы данных
    initialize_database()

    # Загрузка токена из переменных окружения
    token = os.getenv('TELEGRAM_BOT_TOKEN', '8490576810:AAF-wMqonWDLERDi_Wv4r95UYCHt74xWQtQ')

    # Создание приложения
    application = Application.builder().token(token).build()

    # Добавление обработчиков
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('bindgroup', bindgroup))
    application.add_handler(CommandHandler('addadmin', addadmin))
    application.add_handler(CommandHandler('deladmin', deladmin))
    application.add_handler(CommandHandler('listadmins', listadmins))
    application.add_handler(CommandHandler('help', help_command))
    
    # Добавление новых обработчиков экономической системы
    application.add_handler(CommandHandler('balance', balance))
    application.add_handler(CommandHandler('top', top))
    application.add_handler(CommandHandler('pay', pay))
    application.add_handler(CommandHandler('give', give))
    application.add_handler(CommandHandler('getback', getback))
    application.add_handler(CommandHandler('getbalance', getbalance))
    
    # Добавление обработчиков игровых команд
    application.add_handler(CommandHandler('roulette', roulette))
    application.add_handler(CommandHandler('play', play))
    application.add_handler(CommandHandler('russian', russian))
    application.add_handler(CommandHandler('jewish', jewish))
    application.add_handler(CommandHandler('dice', dice))
    application.add_handler(CommandHandler('slots', slots))
    
    # Добавление обработчиков геймификации
    application.add_handler(profile_handler)
    application.add_handler(xp_handler)
    
    # Добавление обработчиков интеграций
    from integrations import register_handlers
    register_handlers(application)
    
    # Добавление обработчика реферальной системы
    from referrals import ref_handler
    application.add_handler(ref_handler)
    
    # Добавление админ-команды загрузки VPN-промокодов
    application.add_handler(CommandHandler('uploadvpn', uploadvpn))
    
    # Регистрация обработчиков админ-панели
    register_admin_handlers(application)
    
    # Регистрация обработчиков новых функций
    from features import register_handlers as register_features_handlers
    register_features_handlers(application)
    # Регистрация обработчиков команд покупки и аренды титулов
    application.add_handler(CommandHandler('buytitle', buytitle_command))
    application.add_handler(CommandHandler('renttitle', renttitle_command))
    # Регистрация обработчика команды просмотра титулов
    application.add_handler(CommandHandler('titles', titles_command))
    
    # Добавляем обработчик всех текстовых сообщений для отслеживания активности
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Настройка JobQueue для напоминаний
    job_queue = application.job_queue
    if job_queue:
        # Добавляем задачу для отправки напоминаний (ежедневно в 12:00)
        from datetime import time
        job_queue.run_daily(send_reminders, time=time(hour=12, minute=0), name='daily_reminders')
        
        # Запускаем фоновую задачу проверки истёкших титулов
        job_queue.run_repeating(check_expired_titles, interval=3600, first=10)  # Проверка каждый час, первая проверка через 10 секунд

    # Запуск бота
    application.run_polling()

async def uploadvpn(update, context):
    """Админ-команда для массовой загрузки VPN-промокодов"""
    user_id = update.effective_user.id
    
    # Проверяем права администратора
    if not is_admin(user_id):
        return
    
    # Проверяем, является ли команда ответом на сообщение
    if not update.message.reply_to_message or not update.message.reply_to_message.text:
        await update.message.reply_text('❌ Используйте команду в ответ на сообщение с промокодами.')
        return
    
    # Получаем текст сообщения с промокодами
    codes_text = update.message.reply_to_message.text
    
    # Парсим промокоды
    codes = []
    for line in codes_text.strip().split('\n'):
        line = line.strip()
        if line:
            parts = line.split(',')
            if len(parts) == 2:
                code, code_type = parts
                codes.append((code.strip(), code_type.strip()))
    
    # Добавляем промокоды в базу данных
    add_vpn_codes(codes)
    
    await update.message.reply_text(f'✅ Загружено {len(codes)} VPN-промокодов.')


if __name__ == '__main__':
    main()