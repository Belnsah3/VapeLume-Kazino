from flask import Flask, request, jsonify
from functools import wraps
import hashlib
import hmac
import os
from database import (
    get_user_balance, update_user_balance, get_user_profile, 
    get_user_achievements, get_referral_count, add_xp,
    get_referrer_id, get_referral_reward_status, mark_referral_reward_as_claimed,
    add_referral, get_user_by_id, can_open_case, update_last_open_case_time
)
from games import roulette, play, russian, jewish, dice, slots
from titles import PERMANENT_TITLES, TEMPORARY_TITLES
from referrals import ref_command
import random
from datetime import datetime
from telegram.ext import ContextTypes
from telegram import Update

app = Flask(__name__)

# Получаем токен бота из переменных окружения
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8490576810:AAF-wMqonWDLERDi_Wv4r95UYCHt74xWQtQ')

def validate_telegram_webapp_data(data: str) -> bool:
    """
    Проверяет подпись данных, полученных от Telegram WebApp
    """
    # Разбиваем данные на пары ключ=значение
    pairs = data.split('&')
    parsed_data = {}
    for pair in pairs:
        key, value = pair.split('=', 1)
        parsed_data[key] = value
    
    # Получаем хэш из данных
    received_hash = parsed_data.get('hash', '')
    
    # Удаляем hash из данных для проверки
    check_data = {k: v for k, v in parsed_data.items() if k != 'hash'}
    
    # Сортируем данные по ключам
    data_check_string = '\n'.join([f'{k}={v}' for k, v in sorted(check_data.items())])
    
    # Создаем секретный ключ
    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
    
    # Создаем хэш данных
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return calculated_hash == received_hash

def verify_webapp_init_data(func):
    """
    Декоратор для проверки initData от Telegram WebApp
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if request.method == 'POST':
            data = request.get_json()
            if not data or 'initData' not in data:
                return jsonify({'success': False, 'message': 'No initData provided'}), 400
            
            # Проверяем подпись initData
            if not validate_telegram_webapp_data(data['initData']):
                return jsonify({'success': False, 'message': 'Invalid initData signature'}), 401
        
        return func(*args, **kwargs)
    
    return wrapper

def get_user_id_from_init_data(init_data: str) -> int:
    """
    Извлекает user_id из initData
    """
    pairs = init_data.split('&')
    for pair in pairs:
        key, value = pair.split('=', 1)
        if key == 'user':
            import json
            user_data = json.loads(value)
            return int(user_data['id'])
    return None

@app.route('/api/user', methods=['POST'])
@verify_webapp_init_data
def get_user_data():
    """
    Возвращает данные пользователя: баланс, уровень, XP, достижения и т.д.
    """
    data = request.get_json()
    user_id = get_user_id_from_init_data(data['initData'])
    
    if not user_id:
        return jsonify({'success': False, 'message': 'Could not extract user ID'}), 400
    
    # Получаем данные пользователя из базы данных
    profile = get_user_profile(user_id)
    level, xp, balance = profile
    
    # Получаем максимальный XP для текущего уровня
    xp_needed = level * 500
    
    # Получаем достижения пользователя
    achievements = get_user_achievements(user_id)
    achievement_list = []
    for achievement_id in achievements:
        # Здесь можно добавить описания достижений
        achievement_list.append({
            'id': achievement_id,
            'name': achievement_id,  # В реальном приложении можно добавить нормальные названия
            'icon': '🏆'  # В реальном приложении можно добавить иконки
        })
    
    # Получаем количество приглашенных пользователей
    referral_count = get_referral_count(user_id)
    
    # Генерируем реферальную ссылку
    bot_username = 'vapelumebot'  # В реальном приложении можно получить это из API Telegram
    referral_link = f'https://t.me/{bot_username}?start=ref{user_id}'
    
    return jsonify({
        'success': True,
        'data': {
            'balance': balance,
            'level': level,
            'xp': xp,
            'xp_needed': xp_needed,
            'rank': get_rank_by_level(level),
            'achievements': achievement_list,
            'referral_link': referral_link,
            'referral_count': referral_count
        }
    })

def get_rank_by_level(level: int) -> str:
    """
    Возвращает звание пользователя на основе уровня
    """
    if level < 5:
        return "Новичок"
    elif level < 10:
        return "Парильщик"
    elif level < 20:
        return "Мастер испарения"
    elif level < 30:
        return "Владыка никотина"
    elif level < 50:
        return "Король испарений"
    else:
        return "Легенда VapeLume"

@app.route('/api/game/<game_type>', methods=['POST'])
@verify_webapp_init_data
def play_game(game_type):
    """
    Обработка игровых запросов
    """
    data = request.get_json()
    user_id = get_user_id_from_init_data(data['initData'])
    
    if not user_id:
        return jsonify({'success': False, 'message': 'Could not extract user ID'}), 400
    
    bet = data.get('bet', 0)
    
    # Проверяем, что игра существует
    if game_type not in ['roulette', 'play', 'russian', 'jewish', 'dice', 'slots']:
        return jsonify({'success': False, 'message': 'Invalid game type'}), 400
    
    # Проверяем баланс пользователя
    balance = get_user_balance(user_id)
    
    # Проверяем минимальные ставки для различных игр
    if game_type in ['roulette'] and bet < 25:
        return jsonify({'success': False, 'message': 'Minimum bet for roulette is 25 LumeCoin'}), 400
    elif game_type in ['dice'] and (bet < 10 or bet > 100):
        return jsonify({'success': False, 'message': 'Bet for dice must be between 10 and 100 LumeCoin'}), 400
    elif game_type in ['slots'] and bet < 50:
        return jsonify({'success': False, 'message': 'Minimum bet for slots is 50 LumeCoin'}), 400
    elif game_type in ['play'] and bet != 25:
        # Для игры play фиксированная ставка 25
        bet = 25
    
    if game_type not in ['russian', 'jewish'] and balance < bet:
        return jsonify({'success': False, 'message': 'Insufficient balance'}), 400
    
    # Выполняем игру
    if game_type == 'roulette':
        return handle_roulette_game(user_id, bet)
    elif game_type == 'play':
        return handle_play_game(user_id)
    elif game_type == 'russian':
        return handle_russian_game(user_id)
    elif game_type == 'jewish':
        return handle_jewish_game(user_id)
    elif game_type == 'dice':
        return handle_dice_game(user_id, bet)
    elif game_type == 'slots':
        return handle_slots_game(user_id, bet)

def handle_roulette_game(user_id: int, bet: float):
    """
    Обработка игры в рулетку
    """
    # Снимаем ставку
    update_user_balance(user_id, -bet)
    
    # Определяем результат (30% шанс выигрыша)
    import random
    result = random.choices(['win', 'lose'], weights=[30, 70])[0]
    
    if result == 'win':
        # Выигрыш (x2)
        win_amount = bet * 2
        update_user_balance(user_id, win_amount)
        winnings = win_amount
    else:
        # Проигрыш
        winnings = 0
    
    new_balance = get_user_balance(user_id)
    
    return jsonify({
        'success': True,
        'winnings': winnings,
        'new_balance': new_balance
    })

def handle_play_game(user_id: int):
    """
    Обработка игры в кости (фиксированная ставка 25)
    """
    bet = 25
    
    # Снимаем ставку
    update_user_balance(user_id, -bet)
    
    # Определяем результат (40% шанс выигрыша)
    import random
    result = random.choices(['win', 'lose'], weights=[40, 60])[0]
    
    if result == 'win':
        # Выигрыш 40 LumeCoin
        win_amount = 40
        update_user_balance(user_id, win_amount)
        winnings = win_amount
    else:
        # Проигрыш
        winnings = 0
    
    new_balance = get_user_balance(user_id)
    
    return jsonify({
        'success': True,
        'winnings': winnings,
        'new_balance': new_balance
    })

def handle_russian_game(user_id: int):
    """
    Обработка русской рулетки (бесплатно, 35% шанс выигрыша)
    """
    # Определяем результат (35% шанс выигрыша)
    import random
    result = random.choices(['win', 'lose'], weights=[35, 65])[0]
    
    if result == 'win':
        # Выигрыш 35 LumeCoin
        win_amount = 35
        update_user_balance(user_id, win_amount)
        winnings = win_amount
    else:
        # Проигрыш
        winnings = 0
    
    new_balance = get_user_balance(user_id)
    
    return jsonify({
        'success': True,
        'winnings': winnings,
        'new_balance': new_balance
    })

def handle_jewish_game(user_id: int):
    """
    Обработка еврейской рулетки (бесплатно, 50% шанс выигрыша)
    """
    # Определяем результат (50% шанс выигрыша)
    import random
    result = random.choices(['win', 'lose'], weights=[50, 50])[0]
    
    if result == 'win':
        # Выигрыш 25 LumeCoin
        win_amount = 25
        update_user_balance(user_id, win_amount)
        winnings = win_amount
    else:
        # Проигрыш 35 LumeCoin или всё, что есть
        balance = get_user_balance(user_id)
        loss_amount = min(35, balance)
        update_user_balance(user_id, -loss_amount)
        winnings = -loss_amount
    
    new_balance = get_user_balance(user_id)
    
    return jsonify({
        'success': True,
        'winnings': abs(winnings) if winnings >= 0 else -abs(winnings),
        'new_balance': new_balance
    })

def handle_dice_game(user_id: int, bet: float):
    """
    Обработка игры в кости с Telegram-анимацией
    """
    # Снимаем ставку
    update_user_balance(user_id, -bet)
    
    # Симулируем бросок кубика (1-6)
    import random
    dice_value = random.randint(1, 6)
    
    if dice_value >= 4:
        # Выигрыш x1.5
        win_amount = bet * 1.5
        update_user_balance(user_id, win_amount)
        winnings = win_amount
    else:
        # Проигрыш
        winnings = 0
    
    new_balance = get_user_balance(user_id)
    
    return jsonify({
        'success': True,
        'winnings': winnings,
        'new_balance': new_balance
    })

def handle_slots_game(user_id: int, bet: float):
    """
    Обработка игры в слоты
    """
    # Снимаем ставку
    update_user_balance(user_id, -bet)
    
    # Симулируем результат слотов (1-64)
    import random
    dice_value = random.randint(1, 64)
    
    if dice_value == 1:
        # Джекпот - 3 совпадения
        win_amount = bet * 5
        update_user_balance(user_id, win_amount)
        winnings = win_amount
    elif 2 <= dice_value <= 7:
        # 2 совпадения
        win_amount = bet * 2
        update_user_balance(user_id, win_amount)
        winnings = win_amount
    else:
        # Проигрыш
        winnings = 0
    
    new_balance = get_user_balance(user_id)
    
    return jsonify({
        'success': True,
        'winnings': winnings,
        'new_balance': new_balance
    })

@app.route('/api/title/buy', methods=['POST'])
@verify_webapp_init_data
def buy_title():
    """
    Покупка или аренда титула
    """
    data = request.get_json()
    user_id = get_user_id_from_init_data(data['initData'])
    
    if not user_id:
        return jsonify({'success': False, 'message': 'Could not extract user ID'}), 400
    
    title = data.get('title')
    title_type = data.get('type', 'permanent')  # 'permanent' или 'temporary'
    
    # Проверяем, существует ли титул
    if title_type == 'permanent':
        if title not in PERMANENT_TITLES:
            return jsonify({'success': False, 'message': 'Invalid permanent title'}), 400
        price = PERMANENT_TITLES[title]
    else:
        if title not in TEMPORARY_TITLES:
            return jsonify({'success': False, 'message': 'Invalid temporary title'}), 400
        price = TEMPORARY_TITLES[title]['price']
    
    # Проверяем баланс пользователя
    balance = get_user_balance(user_id)
    if balance < price:
        return jsonify({'success': False, 'message': 'Insufficient balance'}), 400
    
    # Снимаем средства
    update_user_balance(user_id, -price)
    
    # В реальном приложении здесь нужно было бы:
    # 1. Вызвать соответствующую функцию из titles.py
    # 2. Назначить пользователю титул в чате
    
    # Для упрощения возвращаем успешный результат
    return jsonify({
        'success': True,
        'message': f'Successfully purchased title: {title}'
    })

@app.route('/api/case/open', methods=['POST'])
@verify_webapp_init_data
def open_case():
    """
    Открытие кейса
    """
    data = request.get_json()
    user_id = get_user_id_from_init_data(data['initData'])
    
    if not user_id:
        return jsonify({'success': False, 'message': 'Could not extract user ID'}), 400
    
    # Проверяем, можно ли открыть кейс
    if not can_open_case(user_id):
        return jsonify({'success': False, 'message': 'You already opened a case in the last 24 hours'}), 400
    
    # Стоимость кейса
    case_cost = 10  # В реальности может быть другой
    
    # Проверяем баланс
    balance = get_user_balance(user_id)
    if balance < case_cost:
        return jsonify({'success': False, 'message': 'Insufficient balance to open case'}), 400
    
    # Снимаем стоимость кейса
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
        reward = f'{prize["value"]} {prize["description"]}'
    elif prize['type'] == 'xp':
        add_xp(user_id, prize['value'])
        reward = f'{prize["value"]} {prize["description"]}'
    else:  # rare achievement
        # В реальной реализации можно добавить запись о достижении в БД
        reward = f'{prize["value"]}'
    
    # Обновляем время последнего открытия кейса
    update_last_open_case_time(user_id)
    
    return jsonify({
        'success': True,
        'reward': reward
    })

@app.route('/api/burn', methods=['POST'])
@verify_webapp_init_data
def burn_coins():
    """
    Сжигание монет для получения XP
    """
    data = request.get_json()
    user_id = get_user_id_from_init_data(data['initData'])
    
    if not user_id:
        return jsonify({'success': False, 'message': 'Could not extract user ID'}), 400
    
    amount = data.get('amount', 0)
    
    if amount <= 0:
        return jsonify({'success': False, 'message': 'Invalid amount'}), 400
    
    # Проверяем баланс
    balance = get_user_balance(user_id)
    if balance < amount:
        return jsonify({'success': False, 'message': 'Insufficient balance'}), 400
    
    # Сжигаем монеты и начисляем XP (1:2)
    update_user_balance(user_id, -amount)
    xp_gained = amount * 2
    add_xp(user_id, int(xp_gained))
    
    return jsonify({
        'success': True,
        'xp_gained': int(xp_gained)
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)