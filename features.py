from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
import random
from datetime import datetime, timedelta
from database import (
    get_user_by_id, update_user_balance, add_xp,
    can_open_case, update_last_open_case_time,
    get_active_vote, add_vote_for_option, has_user_voted,
    get_faq_answer, add_faq_entry, get_user_balance
)
import logging

logger = logging.getLogger(__name__)

async def burn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для сжигания LumeCoin в обмен на XP"""
    user_id = update.effective_user.id
    username = update.effective_user.username or str(user_id)
    
    if not context.args:
        await update.message.reply_text('Используйте: /burn [сумма]')
        return
    
    try:
        amount = int(context.args[0])
        if amount <= 0:
            await update.message.reply_text('Сумма должна быть положительной!')
            return
    except ValueError:
        await update.message.reply_text('Некорректная сумма!')
        return
    
    user = get_user_by_id(user_id)
    if not user:
        await update.message.reply_text('Вы не зарегистрированы в системе!')
        return
    
    if user['balance'] < amount:
        await update.message.reply_text(f'Недостаточно средств! Ваш баланс: {user["balance"]} LumeCoin')
        return
    
    # Рассчитываем XP (1 LumeCoin = 2 XP)
    xp_gain = amount * 2
    
    # Обновляем баланс и XP
    update_user_balance(user_id, -amount)
    add_xp(user_id, xp_gain)
    
    await update.message.reply_text(
        f'🔥 Вы сожгли {amount} LumeCoin и получили {xp_gain} XP!\n'
        f'Ваш новый баланс: {get_user_by_id(user_id)["balance"]} LumeCoin\n'
        f'Ваш XP: {get_user_by_id(user_id)["xp"]}'
    )

async def case_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для открытия кейса"""
    user_id = update.effective_user.id
    username = update.effective_user.username or str(user_id)
    
    user = get_user_by_id(user_id)
    if not user:
        await update.message.reply_text('Вы не зарегистрированы в системе!')
        return
    
    # Проверяем, можно ли открыть кейс
    if not can_open_case(user_id):
        await update.message.reply_text('Вы уже открывали кейс в течение последних 24 часов!')
        return
    
    # Стоимость кейса
    case_cost = 100
    if user['balance'] < case_cost:
        await update.message.reply_text(f'Недостаточно средств для открытия кейса! Стоимость: {case_cost} LumeCoin')
        return
    
    # Списываем стоимость кейса
    update_user_balance(user_id, -case_cost)
    
    # Определяем приз
    prizes = [
        {'type': 'coin', 'value': random.randint(50, 200), 'description': 'LumeCoin'},
        {'type': 'xp', 'value': random.randint(50, 300), 'description': 'XP'},
        {'type': 'rare', 'value': 'Редкое достижение', 'description': 'редкое достижение'}
    ]
    
    # Взвешенный выбор приза (меньше шансов на редкий приз)
    weights = [0.7, 0.25, 0.05]  # 70% на монеты, 25% на XP, 5% на редкий приз
    prize = random.choices(prizes, weights=weights, k=1)[0]
    
    # Выдаем приз
    if prize['type'] == 'coin':
        update_user_balance(user_id, prize['value'])
        prize_text = f'{prize["value"]} {prize["description"]}'
    elif prize['type'] == 'xp':
        add_xp(user_id, prize['value'])
        prize_text = f'{prize["value"]} {prize["description"]}'
    else:  # rare achievement
        # В реальной реализации можно добавить запись о достижении в БД
        prize_text = f'{prize["value"]}'
    
    # Обновляем время последнего открытия кейса
    update_last_open_case_time(user_id)
    
    await update.message.reply_text(
        f'🎁 Вы открыли кейс и получили: {prize_text}!\n'
        f'Стоимость кейса ({case_cost} LumeCoin) была списана с вашего баланса.'
    )

async def vote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для голосования"""
    user_id = update.effective_user.id
    username = update.effective_user.username or str(user_id)
    
    # Получаем активное голосование
    active_vote = get_active_vote()
    if not active_vote:
        await update.message.reply_text('На данный момент нет активных голосований.')
        return
    
    vote_id = active_vote['id']
    question = active_vote['question']
    options = active_vote['options']
    
    # Проверяем, голосовал ли пользователь уже
    if has_user_voted(vote_id, user_id):
        await update.message.reply_text('Вы уже проголосовали в этом голосовании!')
        return
    
    # Создаем inline клавиатуру с вариантами ответа
    keyboard = []
    for i, option in enumerate(options):
        callback_data = f'vote_{vote_id}_{i}'
        keyboard.append([InlineKeyboardButton(option, callback_data=callback_data)])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(question, reply_markup=reply_markup)

async def button_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатия кнопки голосования"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Парсим callback_data
    data_parts = query.data.split('_')
    if len(data_parts) != 3 or data_parts[0] != 'vote':
        return
    
    vote_id = int(data_parts[1])
    option_index = int(data_parts[2])
    
    # Проверяем, есть ли активное голосование
    active_vote = get_active_vote()
    if not active_vote or active_vote['id'] != vote_id:
        await query.edit_message_text('Голосование уже завершено.')
        return
    
    # Проверяем, голосовал ли пользователь уже
    if has_user_voted(vote_id, user_id):
        await query.edit_message_text('Вы уже проголосовали в этом голосовании!')
        return
    
    # Добавляем голос
    add_vote_for_option(vote_id, option_index)
    
    await query.edit_message_text(f'✅ Вы проголосовали за: {active_vote["options"][option_index]}')

async def helpme_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI-ассистент / FAQ"""
    if not context.args:
        await update.message.reply_text('Используйте: /helpme [ваш вопрос]')
        return
    
    question = ' '.join(context.args)
    
    # Ищем ответ в FAQ
    answer = get_faq_answer(question)
    
    if answer:
        await update.message.reply_text(f'🔍 Найден ответ на ваш вопрос:\n\n{answer}')
    else:
        await update.message.reply_text(
            '❌ Не удалось найти ответ на ваш вопрос в базе знаний.\n'
            'Попробуйте переформулировать запрос или обратитесь к администратору.'
        )

async def addfaq_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для добавления FAQ (только для админов)"""
    user_id = update.effective_user.id
    
    # Проверяем, является ли пользователь админом
    # Здесь можно использовать функцию из admin_panel.py или свою проверку
    # Для упрощения временно используем список админов
    ADMIN_IDS = [370213481]  # Замените на реальные ID админов
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text('У вас нет прав для выполнения этой команды.')
        return
    
    if len(context.args) < 2:
        await update.message.reply_text('Используйте: /addfaq [вопрос];[ответ]')
        return
    
    # Объединяем аргументы и разделяем по первому вхождению ';'
    full_text = ' '.join(context.args)
    if ';' not in full_text:
        await update.message.reply_text('Используйте: /addfaq [вопрос];[ответ]')
        return
    
    separator_index = full_text.find(';')
    question = full_text[:separator_index].strip()
    answer = full_text[separator_index + 1:].strip()
    
    if not question or not answer:
        await update.message.reply_text('Используйте: /addfaq [вопрос];[ответ]')
        return
    
    # Добавляем запись в FAQ
    add_faq_entry(question, answer)
    
    await update.message.reply_text('✅ Вопрос-ответ успешно добавлены в FAQ.')



def register_handlers(application):
    """Регистрация обработчиков команд"""
    application.add_handler(CommandHandler('burn', burn_command))
    application.add_handler(CommandHandler('case', case_command))
    application.add_handler(CommandHandler('vote', vote_command))
    application.add_handler(CallbackQueryHandler(button_vote, pattern='^vote_'))
    application.add_handler(CommandHandler('helpme', helpme_command))
    application.add_handler(CommandHandler('addfaq', addfaq_command))