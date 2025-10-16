from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputTextMessageContent, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from database import get_total_users_count, get_active_users_today_count, get_total_currency_in_system, get_user_profile, get_user_balance, update_user_balance, ban_user, give_coins_to_all_users, reset_user_balance, get_game_setting, set_game_setting, get_all_user_ids
import logging

def admin_only(func):
    """
    Декоратор, проверяющий, является ли пользователь администратором.
    """
    from functools import wraps
    @wraps(func)
    async def wrapper(update, context):
        user_id = update.effective_user.id
        from database import get_all_admin_ids
        admin_ids = get_all_admin_ids()
        from main import OWNER_ID
        
        if user_id == OWNER_ID or user_id in admin_ids:
            return await func(update, context)
        else:
            # Пользователь не является администратором
            return
    return wrapper


def private_only(func):
    """
    Декоратор, проверяющий, что команда вызвана в приватном чате.
    """
    from functools import wraps
    @wraps(func)
    async def wrapper(update, context):
        if update.effective_chat.type != 'private':
            return  # Игнорировать команду, если она вызвана не в приватном чате
        return await func(update, context)
    return wrapper

logger = logging.getLogger(__name__)

@admin_only
@private_only
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /admin - отображает главное меню админ-панели"""
    keyboard = [
        [InlineKeyboardButton('📊 Статистика', callback_data='admin_stats')],
        [InlineKeyboardButton('👤 Управление пользователями', callback_data='admin_users')],
        [InlineKeyboardButton('💰 Управление экономикой', callback_data='admin_eco')],
        [InlineKeyboardButton('⚙️ Настройки игр', callback_data='admin_games')],
        [InlineKeyboardButton('🎉 Создать ивент', callback_data='admin_event')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text('Админ-панель:', reply_markup=reply_markup)


async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback-запросов админ-панели"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == 'admin_main':
        # Главное меню
        keyboard = [
            [InlineKeyboardButton('📊 Статистика', callback_data='admin_stats')],
            [InlineKeyboardButton('👤 Управление пользователями', callback_data='admin_users')],
            [InlineKeyboardButton('💰 Управление экономикой', callback_data='admin_eco')],
            [InlineKeyboardButton('⚙️ Настройки игр', callback_data='admin_games')],
            [InlineKeyboardButton('🎉 Создать ивент', callback_data='admin_event')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text('Админ-панель:', reply_markup=reply_markup)
    
    elif data == 'admin_stats':
        # Меню статистики
        keyboard = [
            [InlineKeyboardButton('Общее кол-во пользователей', callback_data='admin_stats_users_total')],
            [InlineKeyboardButton('Кол-во активных сегодня', callback_data='admin_stats_users_active')],
            [InlineKeyboardButton('Общая сумма LumeCoin в системе', callback_data='admin_stats_currency_total')],
            [InlineKeyboardButton('🔙 Назад', callback_data='admin_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text('📊 Статистика:', reply_markup=reply_markup)
    
    elif data.startswith('admin_stats_'):
        # Обработка статистики
        if data == 'admin_stats_users_total':
            count = get_total_users_count()
            await query.edit_message_text(f'Общее количество пользователей: {count}')
        elif data == 'admin_stats_users_active':
            count = get_active_users_today_count()
            await query.edit_message_text(f'Количество активных пользователей сегодня: {count}')
        elif data == 'admin_stats_currency_total':
            total = get_total_currency_in_system()
            await query.edit_message_text(f'Общая сумма LumeCoin в системе: {total}')
        
        # Добавляем кнопку назад
        keyboard = [[InlineKeyboardButton('🔙 Назад', callback_data='admin_stats')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_reply_markup(reply_markup=reply_markup)
    
    elif data == 'admin_users':
        # Меню управления пользователями
        keyboard = [
            [InlineKeyboardButton('🔍 Найти пользователя', callback_data='admin_users_search')],
            [InlineKeyboardButton('🔙 Назад', callback_data='admin_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text('👤 Управление пользователями:', reply_markup=reply_markup)
    
    elif data == 'admin_users_search':
        # Запрашиваем ID пользователя для поиска
        await query.edit_message_text('Введите ID пользователя для поиска:')
        
        # Устанавливаем состояние ожидания ID пользователя
        context.user_data['waiting_for_user_id'] = True
    
    elif data.startswith('admin_user_'):
        # Обработка действий с конкретным пользователем
        parts = data.split('_')
        if len(parts) >= 3:
            user_id = int(parts[2])
            action = parts[3] if len(parts) > 3 else None
            
            if action == 'give_coins':
                await query.edit_message_text(f'Введите количество монет для выдачи пользователю {user_id}:')
                context.user_data['waiting_for_coin_amount'] = {'user_id': user_id, 'action': 'give'}
            elif action == 'take_coins':
                await query.edit_message_text(f'Введите количество монет для изъятия у пользователя {user_id}:')
                context.user_data['waiting_for_coin_amount'] = {'user_id': user_id, 'action': 'take'}
            elif action == 'ban':
                # Блокируем пользователя
                ban_user(user_id)
                await query.edit_message_text(f'Пользователь {user_id} успешно заблокирован')
                keyboard = [[InlineKeyboardButton('🔙 Назад', callback_data=f'admin_users_info_{user_id}')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_reply_markup(reply_markup=reply_markup)
    
    elif data == 'admin_eco':
        # Меню управления экономикой
        keyboard = [
            [InlineKeyboardButton('💰 Выдать LumeCoin всем', callback_data='admin_eco_give_all')],
            [InlineKeyboardButton('💸 Обнулить баланс пользователя', callback_data='admin_eco_reset_user')],
            [InlineKeyboardButton('🏷 Управление титулами', callback_data='admin_titles')],
            [InlineKeyboardButton('🔙 Назад', callback_data='admin_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text('💰 Управление экономикой:', reply_markup=reply_markup)
    
    elif data == 'admin_eco_give_all':
        # Подтверждение выдачи монет всем пользователям
        keyboard = [
            [InlineKeyboardButton('✅ Подтвердить', callback_data='admin_eco_give_all_confirm')],
            [InlineKeyboardButton('❌ Отмена', callback_data='admin_eco')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text('Вы уверены, что хотите выдать LumeCoin всем пользователям?', reply_markup=reply_markup)
    
    elif data == 'admin_eco_give_all_confirm':
        # Запрашиваем сумму для выдачи всем пользователям
        await query.edit_message_text('Введите сумму LumeCoin для выдачи всем пользователям:')
        context.user_data['waiting_for_bulk_coin_amount'] = True
    
    elif data == 'admin_eco_reset_user':
        # Запрашиваем ID пользователя для обнуления баланса
        await query.edit_message_text('Введите ID пользователя для обнуления баланса:')
        context.user_data['waiting_for_reset_user_id'] = True
    
    elif data == 'admin_games':
        # Меню настроек игр
        keyboard = [
            [InlineKeyboardButton('🎰 Шанс выигрыша в рулетке', callback_data='admin_games_roulette_chance')],
            [InlineKeyboardButton('🎲 Шанс выигрыша в /play', callback_data='admin_games_play_chance')],
            [InlineKeyboardButton('🔫 Шанс выигрыша в русской рулетке', callback_data='admin_games_russian_chance')],
            [InlineKeyboardButton('✡️ Шанс выигрыша в еврейской рулетке', callback_data='admin_games_jewish_chance')],
            [InlineKeyboardButton('🔙 Назад', callback_data='admin_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text('⚙️ Настройки игр:', reply_markup=reply_markup)
    
    elif data.startswith('admin_games_roulette_chance'):
        # Текущий шанс выигрыша в рулетке
        current_chance = get_game_setting('roulette_win_chance', '30')
        await query.edit_message_text(f'Текущий шанс выигрыша в рулетке: {current_chance}%\nВведите новое значение (0-100):')
        context.user_data['waiting_for_game_setting'] = {'setting': 'roulette_win_chance', 'callback_data': 'admin_games_roulette_chance'}
    
    elif data.startswith('admin_games_play_chance'):
        # Текущий шанс выигрыша в /play
        current_chance = get_game_setting('play_win_chance', '40')
        await query.edit_message_text(f'Текущий шанс выигрыша в /play: {current_chance}%\nВведите новое значение (0-100):')
        context.user_data['waiting_for_game_setting'] = {'setting': 'play_win_chance', 'callback_data': 'admin_games_play_chance'}
    
    elif data.startswith('admin_games_russian_chance'):
        # Текущий шанс выигрыша в русской рулетке
        current_chance = get_game_setting('russian_win_chance', '35')
        await query.edit_message_text(f'Текущий шанс выигрыша в русской рулетке: {current_chance}%\nВведите новое значение (0-100):')
        context.user_data['waiting_for_game_setting'] = {'setting': 'russian_win_chance', 'callback_data': 'admin_games_russian_chance'}
    
    elif data.startswith('admin_games_jewish_chance'):
        # Текущий шанс выигрыша в еврейской рулетке
        current_chance = get_game_setting('jewish_win_chance', '50')
        await query.edit_message_text(f'Текущий шанс выигрыша в еврейской рулетке: {current_chance}%\nВведите новое значение (0-100):')
        context.user_data['waiting_for_game_setting'] = {'setting': 'jewish_win_chance', 'callback_data': 'admin_games_jewish_chance'}
    
    elif data == 'admin_titles':
        # Меню управления титулами
        keyboard = [
            [InlineKeyboardButton('🏷 Постоянные титулы', callback_data='admin_titles_permanent')],
            [InlineKeyboardButton('🕐 Временные титулы', callback_data='admin_titles_temporary')],
            [InlineKeyboardButton('🔙 Назад', callback_data='admin_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text('🏷 Управление титулами:', reply_markup=reply_markup)
    
    elif data.startswith('admin_titles_permanent'):
        # Меню управления постоянными титулами
        from titles import PERMANENT_TITLES
        keyboard = []
        for title, price in PERMANENT_TITLES.items():
            keyboard.append([InlineKeyboardButton(f'{title} - {price} LumeCoin', callback_data=f'admin_title_edit_{title}')])
        keyboard.append([InlineKeyboardButton('➕ Добавить титул', callback_data='admin_title_add_permanent')])
        keyboard.append([InlineKeyboardButton('🔙 Назад', callback_data='admin_titles')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text('🏷 Управление постоянными титулами:', reply_markup=reply_markup)
    
    elif data.startswith('admin_titles_temporary'):
        # Меню управления временными титулами
        from titles import TEMPORARY_TITLES
        keyboard = []
        for title, info in TEMPORARY_TITLES.items():
            keyboard.append([InlineKeyboardButton(f'{title} - {info["price"]} LumeCoin', callback_data=f'admin_title_edit_{title}')])
        keyboard.append([InlineKeyboardButton('➕ Добавить титул', callback_data='admin_title_add_temporary')])
        keyboard.append([InlineKeyboardButton('🔙 Назад', callback_data='admin_titles')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text('🕐 Управление временными титулами:', reply_markup=reply_markup)
    
    elif data.startswith('admin_title_edit_'):
        # Редактирование титула
        title = data.split('_', 3)[3]  # Получаем название титула
        from titles import PERMANENT_TITLES, TEMPORARY_TITLES
        
        # Проверяем, является ли титул постоянным или временным
        is_permanent = title in PERMANENT_TITLES
        if is_permanent:
            current_price = PERMANENT_TITLES[title]
        else:
            # Для временных титулов нужно проверить в TEMPORARY_TITLES
            if title in TEMPORARY_TITLES:
                current_price = TEMPORARY_TITLES[title]['price']
            else:
                # Если титул не найден ни в одном из словарей
                await query.edit_message_text('❌ Титул не найден.')
                return
        
        await query.edit_message_text(f'Текущая цена титула "{title}": {current_price} LumeCoin\nВведите новую цену:')
        context.user_data['waiting_for_title_price'] = {'title': title, 'is_permanent': is_permanent}
    
    elif data == 'admin_title_add_permanent':
        # Добавление нового постоянного титула
        await query.edit_message_text('Введите название нового постоянного титула:')
        context.user_data['waiting_for_new_title_name'] = {'type': 'permanent'}
    
    elif data == 'admin_title_add_temporary':
        # Добавление нового временного титула
        await query.edit_message_text('Введите название нового временного титула:')
        context.user_data['waiting_for_new_title_name'] = {'type': 'temporary'}
    
    elif data == 'admin_event':
        # Меню создания ивента
        await query.edit_message_text('Введите сообщение для отправки всем пользователям:')
        context.user_data['waiting_for_event_message'] = True


async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода пользователя (ID пользователя или суммы монет)"""
    if 'waiting_for_user_id' in context.user_data and context.user_data['waiting_for_user_id']:
        # Обработка ввода ID пользователя
        try:
            user_id = int(update.message.text)
            context.user_data['waiting_for_user_id'] = False
            
            # Получаем информацию о пользователе
            level, xp, balance = get_user_profile(user_id)
            
            # Формируем сообщение с информацией о пользователе
            user_info = f'Информация о пользователе {user_id}:\n'
            user_info += f'Уровень: {level}\n'
            user_info += f'Опыт: {xp}\n'
            user_info += f'Баланс: {balance} LumeCoin\n'
            
            # Создаем клавиатуру с действиями
            keyboard = [
                [InlineKeyboardButton('💰 Выдать монеты', callback_data=f'admin_user_{user_id}_give_coins')],
                [InlineKeyboardButton('💸 Забрать монеты', callback_data=f'admin_user_{user_id}_take_coins')],
                [InlineKeyboardButton('🚫 Выдать бан', callback_data=f'admin_user_{user_id}_ban')],
                [InlineKeyboardButton('🔙 Назад', callback_data='admin_users')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(user_info, reply_markup=reply_markup)
            
        except ValueError:
            await update.message.reply_text('Некорректный ID пользователя. Пожалуйста, введите числовое значение.')
    
    elif 'waiting_for_coin_amount' in context.user_data:
        # Обработка ввода суммы монет
        try:
            amount = float(update.message.text)
            user_data = context.user_data['waiting_for_coin_amount']
            user_id = user_data['user_id']
            action = user_data['action']
            
            if action == 'give':
                # Выдаем монеты пользователю
                update_user_balance(user_id, amount)
                await update.message.reply_text(f'Пользователю {user_id} выдано {amount} LumeCoin')
            elif action == 'take':
                # Изымаем монеты у пользователя (передаем отрицательное значение)
                update_user_balance(user_id, -amount)
                await update.message.reply_text(f'У пользователя {user_id} изъято {amount} LumeCoin')
            
            # Убираем флаг ожидания
            del context.user_data['waiting_for_coin_amount']
            
            # Возвращаемся к информации о пользователе
            level, xp, balance = get_user_profile(user_id)
            user_info = f'Информация о пользователе {user_id}:\n'
            user_info += f'Уровень: {level}\n'
            user_info += f'Опыт: {xp}\n'
            user_info += f'Баланс: {balance} LumeCoin\n'
            
            # Создаем клавиатуру с действиями
            keyboard = [
                [InlineKeyboardButton('💰 Выдать монеты', callback_data=f'admin_user_{user_id}_give_coins')],
                [InlineKeyboardButton('💸 Забрать монеты', callback_data=f'admin_user_{user_id}_take_coins')],
                [InlineKeyboardButton('🚫 Выдать бан', callback_data=f'admin_user_{user_id}_ban')],
                [InlineKeyboardButton('🔙 Назад', callback_data='admin_users')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(user_info, reply_markup=reply_markup)
            
        except ValueError:
            await update.message.reply_text('Некорректное значение. Пожалуйста, введите числовое значение.')
    
    elif 'waiting_for_bulk_coin_amount' in context.user_data and context.user_data['waiting_for_bulk_coin_amount']:
        # Обработка ввода суммы для выдачи всем пользователям
        try:
            amount = float(update.message.text)
            context.user_data['waiting_for_bulk_coin_amount'] = False
            
            # Выдаем монеты всем пользователям
            give_coins_to_all_users(amount)
            await update.message.reply_text(f'Всем пользователям выдано {amount} LumeCoin')
            
            # Убираем флаг ожидания
            del context.user_data['waiting_for_bulk_coin_amount']
            
        except ValueError:
            await update.message.reply_text('Некорректное значение. Пожалуйста, введите числовое значение.')
    
    elif 'waiting_for_reset_user_id' in context.user_data and context.user_data['waiting_for_reset_user_id']:
        # Обработка ввода ID пользователя для обнуления баланса
        try:
            user_id = int(update.message.text)
            context.user_data['waiting_for_reset_user_id'] = False
            
            # Обнуляем баланс пользователя
            reset_user_balance(user_id)
            await update.message.reply_text(f'Баланс пользователя {user_id} успешно обнулен')
            
        except ValueError:
            await update.message.reply_text('Некорректный ID пользователя. Пожалуйста, введите числовое значение.')
    
    elif 'waiting_for_game_setting' in context.user_data:
        # Обработка ввода значения настройки игры
        try:
            value = float(update.message.text)
            if 0 <= value <= 100:
                setting_data = context.user_data['waiting_for_game_setting']
                setting_key = setting_data['setting']
                
                # Устанавливаем новое значение настройки
                set_game_setting(setting_key, str(value))
                
                await update.message.reply_text(f'Настройка "{setting_key}" успешно изменена на {value}%')
                
                # Убираем флаг ожидания
                del context.user_data['waiting_for_game_setting']
            else:
                await update.message.reply_text('Значение должно быть в диапазоне от 0 до 100. Пожалуйста, введите корректное значение:')
        except ValueError:
            await update.message.reply_text('Некорректное значение. Пожалуйста, введите числовое значение:')
    
    elif 'waiting_for_event_message' in context.user_data and context.user_data['waiting_for_event_message']:
        # Обработка ввода сообщения для ивента
        event_message = update.message.text
        context.user_data['waiting_for_event_message'] = False
        
        # Получаем всех пользователей
        user_ids = get_all_user_ids()
        
        # Отправляем сообщение всем пользователям
        successful_sends = 0
        for user_id in user_ids:
            try:
                await context.bot.send_message(chat_id=user_id, text=f'🎉 СООБЩЕНИЕ ОТ АДМИНИСТРАЦИИ:\n\n{event_message}')
                successful_sends += 1
            except Exception:
                # Если не удалось отправить сообщение пользователю (например, бот заблокирован), пропускаем
                pass
        
        await update.message.reply_text(f'Сообщение ивента успешно отправлено {successful_sends} пользователям из {len(user_ids)}')
        
        # Убираем флаг ожидания
        del context.user_data['waiting_for_event_message']
    
    elif 'waiting_for_title_price' in context.user_data:
        # Обработка ввода новой цены титула
        try:
            new_price = int(update.message.text)
            if new_price <= 0:
                await update.message.reply_text('Цена должна быть положительным числом. Пожалуйста, введите корректное значение:')
                return
            
            title_data = context.user_data['waiting_for_title_price']
            title = title_data['title']
            is_permanent = title_data['is_permanent']
            
            # Обновляем цену титула
            if is_permanent:
                # Для постоянных титулов нужно импортировать и обновить словарь PERMANENT_TITLES
                from titles import PERMANENT_TITLES
                if title in PERMANENT_TITLES:
                    PERMANENT_TITLES[title] = new_price
                    await update.message.reply_text(f'Цена титула "{title}" успешно изменена на {new_price} LumeCoin')
                else:
                    await update.message.reply_text('Титул не найден.')
            else:
                # Для временных титулов нужно импортировать и обновить словарь TEMPORARY_TITLES
                from titles import TEMPORARY_TITLES
                if title in TEMPORARY_TITLES:
                    TEMPORARY_TITLES[title]['price'] = new_price
                    await update.message.reply_text(f'Цена титула "{title}" успешно изменена на {new_price} LumeCoin')
                else:
                    await update.message.reply_text('Титул не найден.')
            
            # Убираем флаг ожидания
            del context.user_data['waiting_for_title_price']
            
        except ValueError:
            await update.message.reply_text('Некорректное значение. Пожалуйста, введите числовое значение:')
    
    elif 'waiting_for_new_title_name' in context.user_data:
        # Обработка ввода названия нового титула
        title_name = update.message.text.strip()
        
        # Проверяем, что название не пустое
        if not title_name:
            await update.message.reply_text('Название титула не может быть пустым. Пожалуйста, введите корректное название:')
            return
        
        title_info = context.user_data['waiting_for_new_title_name']
        title_type = title_info['type']
        
        # Запрашиваем цену для нового титула
        await update.message.reply_text(f'Введите цену для титула "{title_name}":')
        context.user_data['waiting_for_new_title_price'] = {'name': title_name, 'type': title_type}
    
    elif 'waiting_for_new_title_price' in context.user_data:
        # Обработка ввода цены нового титула
        try:
            price = int(update.message.text)
            if price <= 0:
                await update.message.reply_text('Цена должна быть положительным числом. Пожалуйста, введите корректное значение:')
                return
            
            title_info = context.user_data['waiting_for_new_title_price']
            title_name = title_info['name']
            title_type = title_info['type']
            
            # Добавляем новый титул
            if title_type == 'permanent':
                from titles import PERMANENT_TITLES
                PERMANENT_TITLES[title_name] = price
                await update.message.reply_text(f'Постоянный титул "{title_name}" успешно добавлен с ценой {price} LumeCoin')
            else:  # temporary
                from titles import TEMPORARY_TITLES
                # Запрашиваем длительность для временного титула
                await update.message.reply_text(f'Введите длительность титула "{title_name}" в днях:')
                context.user_data['waiting_for_new_title_duration'] = {'name': title_name, 'price': price}
            
            # Убираем флаг ожидания цены
            del context.user_data['waiting_for_new_title_price']
            
        except ValueError:
            await update.message.reply_text('Некорректное значение. Пожалуйста, введите числовое значение:')
    
    elif 'waiting_for_new_title_duration' in context.user_data:
        # Обработка ввода длительности нового временного титула
        try:
            duration = int(update.message.text)
            if duration <= 0:
                await update.message.reply_text('Длительность должна быть положительным числом. Пожалуйста, введите корректное значение:')
                return
            
            title_info = context.user_data['waiting_for_new_title_duration']
            title_name = title_info['name']
            price = title_info['price']
            
            # Добавляем новый временный титул
            from titles import TEMPORARY_TITLES
            TEMPORARY_TITLES[title_name] = {'price': price, 'duration_days': duration}
            await update.message.reply_text(f'Временный титул "{title_name}" успешно добавлен с ценой {price} LumeCoin и длительностью {duration} дней')
            
            # Убираем флаг ожидания
            del context.user_data['waiting_for_new_title_duration']
            
        except ValueError:
            await update.message.reply_text('Некорректное значение. Пожалуйста, введите числовое значение:')


def register_admin_handlers(application):
    """Регистрация обработчиков админ-панели"""
    application.add_handler(CommandHandler('admin', admin_command))
    application.add_handler(CallbackQueryHandler(admin_callback_handler, pattern='^admin_'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_input))