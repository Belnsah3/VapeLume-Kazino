import asyncio
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters, CommandHandler
from database import add_xp, get_user_profile, get_user_achievements, grant_achievement

def group_only(func):
    """
    Декоратор, который проверяет, что команда вызвана в привязанной супергруппе.
    """
    from functools import wraps
    @wraps(func)
    async def wrapper(update, context):
        # Импортируем здесь, чтобы избежать циклической зависимости
        from database import get_bound_supergroup_id
        
        chat_id = update.effective_chat.id
        bound_supergroup_id = get_bound_supergroup_id()
        
        # Проверяем, что чат - это привязанная супергруппа
        if update.effective_chat.type not in ['group', 'supergroup'] or chat_id != bound_supergroup_id:
            return  # Игнорировать команду, если она вызвана не в привязанной супергруппе
        
        return await func(update, context)
    return wrapper

# Константы для геймификации
XP_PER_MESSAGE = 10
XP_LEVEL_THRESHOLD = 500  # Опыт, необходимый для повышения уровня (базовый)
COOLDOWN_SECONDS = 60 # Кулдаун в секундах между начислениями XP за сообщения

# Словарь для отслеживания времени последнего получения XP пользователем
last_xp_time = {}

# Словарь званий в зависимости от уровня
LEVEL_TITLES = {
    (1, 5): "Новичок",
    (6, 10): "Парильщик",
    (11, 20): "Знаток Вейпа",
    (21, 30): "Маг Вейпа",
    (31, 40): "Владыка Картриджа",
    (41, 50): "Император Облак",
    (51, 100): "Бог Вейпинга"
}

# Словарь достижений
ACHIEVEMENTS = {
    "first_message": {"name": "Первое сообщение", "condition": lambda user_data: user_data['messages_sent'] >= 1},
    "level_5": {"name": "Достиг 5 уровня", "condition": lambda user_data: user_data['level'] >= 5},
    "level_10": {"name": "Достиг 10 уровня", "condition": lambda user_data: user_data['level'] >= 10},
    "play_10_games": {"name": "Сыграл в 10 игр", "condition": lambda user_data: user_data['games_played'] >= 10},
    "play_50_games": {"name": "Сыграл в 50 игр", "condition": lambda user_data: user_data['games_played'] >= 50},
    "first_win": {"name": "Первый выигрыш", "condition": lambda user_data: user_data['games_won'] >= 1},
    "top_10": {"name": "В топ-10", "condition": lambda user_data: user_data['is_top_10']},
    "loyal_member": {"name": "Завсегдатай", "condition": lambda user_data: user_data['days_active'] >= 7}
}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик сообщений для начисления XP
    """
    user_id = update.effective_user.id
    
    # Проверяем, что сообщение отправлено в привязанной группе
    chat_id = update.effective_chat.id
    from database import get_bound_supergroup_id
    bound_supergroup_id = get_bound_supergroup_id()
    
    if update.effective_chat.type not in ['group', 'supergroup'] or chat_id != bound_supergroup_id:
        return  # Игнорировать сообщения, не из привязанной супергруппы
    
    # Проверяем кулдаун
    current_time = asyncio.get_event_loop().time()
    if user_id in last_xp_time:
        time_since_last_xp = current_time - last_xp_time[user_id]
        if time_since_last_xp < COOLDOWN_SECONDS:
            return  # Не начисляем XP, если прошло мало времени
    
    # Начисляем XP
    new_level, new_xp = add_xp(user_id, XP_PER_MESSAGE)
    last_xp_time[user_id] = current_time
    
    # Обновляем статистику сообщений пользователя
    if 'messages_sent' not in context.user_data:
        context.user_data['messages_sent'] = 0
    context.user_data['messages_sent'] += 1
    
    # Проверяем, открыл ли пользователь новое достижение
    await check_achievements(update, context, user_id, new_level)

async def check_achievements(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, current_level: int):
    """
    Проверяет, открыл ли пользователь новые достижения
    """
    # Получаем текущие данные пользователя для проверки достижений
    level, xp, balance = get_user_profile(user_id)
    
    # Обновляем данные пользователя для проверки условий
    user_data = {
        'level': current_level,
        'messages_sent': context.user_data.get('messages_sent', 0),
        'games_played': context.user_data.get('games_played', 0),
        'games_won': context.user_data.get('games_won', 0),
        'is_top_10': False,  # Это условие требует дополнительной проверки
        'days_active': context.user_data.get('days_active', 0)
    }
    
    # Проверяем все достижения
    for achievement_id, achievement_info in ACHIEVEMENTS.items():
        # Проверяем, есть ли у пользователя это достижение
        user_achievements = get_user_achievements(user_id)
        if achievement_id not in user_achievements:
            # Проверяем, выполнено ли условие для получения достижения
            if achievement_info['condition'](user_data):
                # Начисляем достижение
                grant_achievement(user_id, achievement_id)
                
                # Отправляем поздравительное сообщение
                await update.message.reply_text(
                    f"🎉 Поздравляем! Вы получили достижение: {achievement_info['name']}!"
                )

def get_level_title(level: int) -> str:
    """
    Возвращает звание в зависимости от уровня
    """
    for (min_level, max_level), title in LEVEL_TITLES.items():
        if min_level <= level <= max_level:
            return title
    return "Легенда"

def format_xp_progress(level: int, xp: int) -> str:
    """
    Форматирует прогресс XP в виде строки с визуальным прогресс-баром
    """
    # Рассчитываем максимальный XP для текущего уровня
    max_xp_for_level = level * XP_LEVEL_THRESHOLD
    progress = min(int((xp / max_xp_for_level) * 10), 10)  # От 0 до 10
    
    # Создаем прогресс-бар
    progress_bar = "█" * progress + "░" * (10 - progress)
    
    return f"[{progress_bar}] {xp}/{max_xp_for_level} XP"

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /profile для отображения профиля пользователя
    """
    user_id = update.effective_user.id
    
    # Получаем данные профиля
    level, xp, balance = get_user_profile(user_id)
    
    # Получаем список достижений
    achievements = get_user_achievements(user_id)
    
    # Получаем звание
    title = get_level_title(level)
    
    # Форматируем прогресс XP
    xp_progress = format_xp_progress(level, xp)
    
    # Формируем сообщение профиля
    profile_message = f"👤 Профиль пользователя: {update.effective_user.full_name}\n\n"
    profile_message += f"🏆 Уровень: {level} ({title})\n"
    profile_message += f"📊 Опыт: {xp_progress}\n"
    profile_message += f"💰 Баланс: {balance} LumeCoin\n\n"
    
    if achievements:
        profile_message += "🎖 Достижения:\n"
        for achievement_id in achievements:
            achievement_name = ACHIEVEMENTS.get(achievement_id, {}).get('name', achievement_id)
            profile_message += f"• {achievement_name}\n"
    else:
        profile_message += "🎖 Достижения: пока нет"
    
    await update.message.reply_text(profile_message)

# Обработчики для регистрации в main.py
xp_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
profile_handler = CommandHandler('profile', profile)