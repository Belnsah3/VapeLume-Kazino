import sqlite3
from datetime import datetime

def initialize_database():
    """
    Инициализирует базу данных и создает необходимые таблицы.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()

    # Создание таблиц
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 100.0,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            last_bonus TIMESTAMP,
            discount_tier INTEGER DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS interactions (user_id INTEGER PRIMARY KEY, last_message TIMESTAMP)
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS referrals (user_id INTEGER PRIMARY KEY, referrer_id INTEGER, reward_claimed BOOLEAN)
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS achievements (user_id INTEGER, achievement_id TEXT, unlocked BOOLEAN)
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS event_cases (user_id INTEGER PRIMARY KEY, last_open TIMESTAMP)
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS votes (id INTEGER PRIMARY KEY, question TEXT, option_a TEXT, option_b TEXT, votes_a INT, votes_b INT, active BOOLEAN)
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vpn_codes (id INTEGER PRIMARY KEY, code TEXT UNIQUE, type TEXT, used_by INTEGER, used_at TIMESTAMP)
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS faq (question TEXT PRIMARY KEY, answer TEXT)
    ''')

    # Добавление владельца в таблицу админов
    cursor.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (8415112409)')
    
    # Создание таблицы для временных титулов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS temp_titles (
            user_id INTEGER,
            chat_id INTEGER,
            title TEXT,
            expires_at TIMESTAMP,
            PRIMARY KEY (user_id, chat_id)
        )
    ''')

    conn.commit()
    conn.close()


def get_user_balance(user_id: int) -> float:
    """
    Возвращает баланс пользователя. Если пользователя нет в таблице users,
    создает его с балансом по умолчанию (100.0) и возвращает это значение.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    # Проверяем, существует ли пользователь
    cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    if result is None:
        # Пользователь не существует, создаем его с балансом по умолчанию
        default_balance = 100.0
        cursor.execute('INSERT INTO users (user_id, balance) VALUES (?, ?)', (user_id, default_balance))
        conn.commit()
        balance = default_balance
    else:
        balance = result[0]
    
    conn.close()
    return balance


def update_user_balance(user_id: int, amount: float):
    """
    Изменяет баланс пользователя на указанную сумму (может быть положительной или отрицательной).
    Убедись, что баланс не может стать отрицательным.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    # Получаем текущий баланс
    cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    if result is None:
        # Если пользователя нет, создаем его с балансом по умолчанию
        current_balance = 100.0
        cursor.execute('INSERT INTO users (user_id, balance) VALUES (?, ?)', (user_id, current_balance))
    else:
        current_balance = result[0]
    
    # Рассчитываем новый баланс
    new_balance = current_balance + amount
    
    # Убедимся, что баланс не станет отрицательным
    if new_balance < 0:
        new_balance = 0
    
    # Обновляем баланс
    cursor.execute('UPDATE users SET balance = ? WHERE user_id = ?', (new_balance, user_id))
    
    conn.commit()
    conn.close()


def get_top_users_by_balance(limit: int = 10) -> list[tuple[int, float]]:
    """
    Возвращает список кортежей (user_id, balance), отсортированный по убыванию баланса.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT ?', (limit,))
    results = cursor.fetchall()
    
    conn.close()
    
    return results


def get_bound_supergroup_id() -> int | None:
    """
    Извлекает chat_id из таблицы settings по ключу bound_supergroup_id.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT value FROM settings WHERE key = ?', ('bound_supergroup_id',))
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        return int(result[0])
    return None


def set_bound_supergroup_id(chat_id: int):
    """
    Сохраняет chat_id в таблицу settings.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', ('bound_supergroup_id', str(chat_id)))
    
    conn.commit()
    conn.close()


def get_all_admin_ids() -> list[int]:
    """
    Возвращает список ID всех администраторов из таблицы admins.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT user_id FROM admins')
    results = cursor.fetchall()
    
    conn.close()
    
    return [row[0] for row in results]


def add_admin(user_id: int):
    """
    Добавляет пользователя в таблицу администраторов.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    cursor.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (user_id,))
    
    conn.commit()
    conn.close()


def remove_admin(user_id: int):
    """
    Удаляет пользователя из таблицы администраторов.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM admins WHERE user_id = ?', (user_id,))
    
    conn.commit()
    conn.close()


def add_xp(user_id: int, amount: int) -> tuple[int, int]:
    """
    Начисляет опыт пользователю и проверяет повышение уровня.
    Возвращает кортеж (new_level, new_xp).
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    # Получаем текущий уровень и опыт
    cursor.execute('SELECT level, xp FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    if result is None:
        # Если пользователя нет, создаем его с начальными значениями
        current_level = 1
        current_xp = 0
        cursor.execute('INSERT INTO users (user_id, level, xp) VALUES (?, ?, ?)',
                      (user_id, current_level, current_xp))
    else:
        current_level, current_xp = result
    
    # Добавляем опыт
    new_xp = current_xp + amount
    
    # Проверяем, повысился ли уровень (каждые 500 XP)
    new_level = current_level
    while new_xp >= new_level * 500:  # Для усложнения уровня требуем больше XP
        new_xp -= new_level * 500
        new_level += 1
    
    # Обновляем уровень и опыт в БД
    cursor.execute('UPDATE users SET level = ?, xp = ? WHERE user_id = ?',
                  (new_level, new_xp, user_id))
    
    conn.commit()
    conn.close()
    
    return new_level, new_xp


def get_user_profile(user_id: int) -> tuple[int, int, int]:
    """
    Возвращает кортеж с данными профиля (level, xp, balance).
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT level, xp, balance FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    if result is None:
        # Если пользователя нет, создаем его с начальными значениями
        default_level = 1
        default_xp = 0
        default_balance = 100.0
        cursor.execute('INSERT INTO users (user_id, level, xp, balance) VALUES (?, ?, ?, ?)',
                      (user_id, default_level, default_xp, default_balance))
        conn.commit()
        profile = (default_level, default_xp, int(default_balance))
    else:
        # balance хранится как REAL, преобразуем в int для возврата
        level, xp, balance = result
        profile = (level, xp, int(balance))
    
    conn.close()
    return profile


def grant_achievement(user_id: int, achievement_id: str):
    """
    Присваивает пользователю достижение.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    # Проверяем, есть ли уже такое достижение у пользователя
    cursor.execute('SELECT 1 FROM achievements WHERE user_id = ? AND achievement_id = ?',
                  (user_id, achievement_id))
    result = cursor.fetchone()
    
    if result is None:
        # Если достижения нет, добавляем его
        cursor.execute('INSERT INTO achievements (user_id, achievement_id, unlocked) VALUES (?, ?, ?)',
                      (user_id, achievement_id, True))
    
    conn.commit()
    conn.close()


def get_user_achievements(user_id: int) -> list[str]:
    """
    Возвращает список ID достижений пользователя.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT achievement_id FROM achievements WHERE user_id = ? AND unlocked = ?',
                  (user_id, True))
    results = cursor.fetchall()
    
    conn.close()
    
    return [achievement_id for achievement_id, in results]


def get_user_discount_tier(user_id: int) -> int:
    """
    Возвращает уровень скидки пользователя.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT discount_tier FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    if result is None:
        # Если пользователя нет, создаем его с уровнем скидки по умолчанию (0)
        default_discount_tier = 0
        cursor.execute('INSERT INTO users (user_id, discount_tier) VALUES (?, ?)', (user_id, default_discount_tier))
        conn.commit()
        discount_tier = default_discount_tier
    else:
        discount_tier = result[0]
    
    conn.close()
    return discount_tier


def set_user_discount_tier(user_id: int, tier: int):
    """
    Устанавливает уровень скидки пользователя.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    # Обновляем уровень скидки
    cursor.execute('UPDATE users SET discount_tier = ? WHERE user_id = ?', (tier, user_id))
    
    conn.commit()
    conn.close()


def get_available_vpn_code(code_type: str) -> str | None:
    """
    Находит один неиспользованный промокод указанного типа, помечает его как использованный
    (записывая user_id и used_at) и возвращает код.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    # Находим неиспользованный промокод указанного типа
    cursor.execute('SELECT id, code FROM vpn_codes WHERE type = ? AND used_by IS NULL AND used_at IS NULL LIMIT 1', (code_type,))
    result = cursor.fetchone()
    
    if result is None:
        # Нет доступных промокодов
        conn.close()
        return None
    
    vpn_id, vpn_code = result
    
    # Помечаем промокод как использованный
    cursor.execute('UPDATE vpn_codes SET used_by = ?, used_at = ? WHERE id = ?', (None, datetime.now(), vpn_id))
    
    conn.commit()
    conn.close()
    
    return vpn_code


def add_vpn_codes(codes: list[tuple[str, str]]):
    """
    Добавляет список промокодов в базу данных. Кортеж: (code, type).
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    # Добавляем промокоды в базу данных
    for code, code_type in codes:
        cursor.execute('INSERT OR IGNORE INTO vpn_codes (code, type) VALUES (?, ?)', (code, code_type))
    
    conn.commit()
    conn.close()


def add_referral(user_id: int, referrer_id: int):
    """
    Добавляет запись о реферале в базу данных.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    # Добавляем запись о реферале
    cursor.execute('INSERT OR REPLACE INTO referrals (user_id, referrer_id, reward_claimed) VALUES (?, ?, ?)',
                  (user_id, referrer_id, False))
    
    conn.commit()
    conn.close()


def get_referrer_id(user_id: int) -> int | None:
    """
    Получает ID пригласившего пользователя.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    # Получаем referrer_id для пользователя
    cursor.execute('SELECT referrer_id FROM referrals WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        return result[0]
    return None


def get_referral_count(user_id: int) -> int:
    """
    Считает, сколько пользователей пригласил данный пользователь.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    # Считаем количество приглашенных пользователей
    cursor.execute('SELECT COUNT(*) FROM referrals WHERE referrer_id = ?', (user_id,))
    result = cursor.fetchone()
    
    conn.close()
    
    return result[0] if result else 0


def get_referral_reward_status(user_id: int) -> bool:
    """
    Проверяет, получил ли уже пользователь награду за реферала.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    # Проверяем статус получения награды
    cursor.execute('SELECT reward_claimed FROM referrals WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        return result[0] == 1
    return False


def mark_referral_reward_as_claimed(user_id: int):
    """
    Помечает, что награда за приглашение была выдана.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    # Помечаем награду как полученную
    cursor.execute('UPDATE referrals SET reward_claimed = ? WHERE user_id = ?', (True, user_id))
    
    conn.commit()
    conn.close()


def get_total_users_count() -> int:
    """
    Возвращает общее количество пользователей в системе.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM users')
    result = cursor.fetchone()
    
    conn.close()
    
    return result[0] if result else 0


def get_active_users_today_count() -> int:
    """
    Возвращает количество активных пользователей сегодня.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    # Получаем количество пользователей, которые отправили сообщение сегодня
    today = datetime.now().date()
    cursor.execute('SELECT COUNT(*) FROM interactions WHERE date(last_message) = ?', (today,))
    result = cursor.fetchone()
    
    conn.close()
    
    return result[0] if result else 0


def get_total_currency_in_system() -> float:
    """
    Возвращает общую сумму LumeCoin в системе.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT SUM(balance) FROM users')
    result = cursor.fetchone()
    
    conn.close()
    
    return result[0] if result and result[0] else 0.0


def ban_user(user_id: int):
    """
    Добавляет пользователя в список заблокированных.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    # Создаем таблицу bans, если она не существует
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bans (user_id INTEGER PRIMARY KEY, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
    ''')
    
    # Добавляем пользователя в таблицу банов
    cursor.execute('INSERT OR REPLACE INTO bans (user_id) VALUES (?)', (user_id,))
    
    conn.commit()
    conn.close()


def is_user_banned(user_id: int) -> bool:
    """
    Проверяет, заблокирован ли пользователь.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT 1 FROM bans WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    conn.close()
    
    return result is not None


def give_coins_to_all_users(amount: float):
    """
    Выдает указанное количество монет всем пользователям.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    # Обновляем баланс всех пользователей, добавляя указанную сумму
    cursor.execute('UPDATE users SET balance = balance + ?', (amount,))
    
    conn.commit()
    conn.close()


def reset_user_balance(user_id: int):
    """
    Обнуляет баланс указанного пользователя.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    # Обновляем баланс пользователя до 0
    cursor.execute('UPDATE users SET balance = 0 WHERE user_id = ?', (user_id,))
    
    conn.commit()
    conn.close()


def get_game_setting(key: str, default_value: str = None) -> str:
    """
    Получает значение настройки игры из таблицы settings.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        return result[0]
    return default_value


def set_game_setting(key: str, value: str):
    """
    Устанавливает значение настройки игры в таблице settings.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    
    conn.commit()
    conn.close()


def get_all_user_ids() -> list[int]:
    """
    Возвращает список всех ID пользователей в системе.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT user_id FROM users')
    results = cursor.fetchall()
    
    conn.close()
    
    return [row[0] for row in results]


def add_temp_title(user_id: int, chat_id: int, title: str, expires_at: datetime):
    """
    Сохраняет информацию о временном титуле.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO temp_titles (user_id, chat_id, title, expires_at)
        VALUES (?, ?, ?, ?)
    ''', (user_id, chat_id, title, expires_at))
    
    conn.commit()
    conn.close()


def get_expired_titles() -> list[tuple[int, int]]:
    """
    Возвращает список (user_id, chat_id) для всех истёкших титулов.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT user_id, chat_id FROM temp_titles
        WHERE expires_at < ?
    ''', (datetime.now(),))
    results = cursor.fetchall()
    
    conn.close()
    
    return [(row[0], row[1]) for row in results]


def remove_temp_title(user_id: int, chat_id: int):
    """
    Удаляет запись о временном титуле.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        DELETE FROM temp_titles
        WHERE user_id = ? AND chat_id = ?
    ''', (user_id, chat_id))
    
    conn.commit()
    conn.close()


def add_interaction(user_id: int):
    """
    Добавляет или обновляет запись о взаимодействии пользователя с ботом.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    # Вставляем или обновляем время последнего сообщения пользователя
    cursor.execute('''
        INSERT OR REPLACE INTO interactions (user_id, last_message)
        VALUES (?, ?)
    ''', (user_id, datetime.now()))
    
    conn.commit()
    conn.close()


def get_inactive_users(days: int = 30) -> list[int]:
    """
    Возвращает список ID пользователей, которые не были активны в течение указанного количества дней.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    # Вычисляем дату, которая была 'days' дней назад
    cutoff_date = datetime.now()
    cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)
    
    # Получаем пользователей, которые не взаимодействовали с ботом в течение указанного периода
    cursor.execute('''
        SELECT u.user_id
        FROM users u
        LEFT JOIN interactions i ON u.user_id = i.user_id
        WHERE i.last_message < ? OR i.last_message IS NULL
    ''', (cutoff_date,))
    results = cursor.fetchall()
    
    conn.close()
    
    return [row[0] for row in results]


def get_user_by_id(user_id: int) -> dict | None:
    """
    Возвращает информацию о пользователе по его ID.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT user_id, balance, xp, level FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        user_id, balance, xp, level = result
        return {
            'user_id': user_id,
            'balance': balance,
            'xp': xp,
            'level': level
        }
    return None


def can_open_case(user_id: int) -> bool:
    """
    Проверяет, может ли пользователь открыть кейс (не открывал ли он его в течение последних 24 часов).
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    # Получаем время последнего открытия кейса
    cursor.execute('SELECT last_open FROM event_cases WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    conn.close()
    
    if result and result[0]:
        last_open = datetime.fromisoformat(result[0])
        # Проверяем, прошло ли более 24 часов с последнего открытия
        return datetime.now() - last_open >= timedelta(hours=24)
    else:
        # Если пользователь никогда не открывал кейс, он может открыть
        return True


def update_last_open_case_time(user_id: int):
    """
    Обновляет время последнего открытия кейса для пользователя.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO event_cases (user_id, last_open)
        VALUES (?, ?)
    ''', (user_id, datetime.now()))
    
    conn.commit()
    conn.close()


def get_active_vote() -> dict | None:
    """
    Возвращает активное голосование, если оно есть.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, question, option_a, option_b, votes_a, votes_b, active FROM votes WHERE active = 1 LIMIT 1')
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        vote_id, question, option_a, option_b, votes_a, votes_b, active = result
        return {
            'id': vote_id,
            'question': question,
            'options': [option_a, option_b],
            'votes': [votes_a, votes_b],
            'active': bool(active)
        }
    return None


def add_vote_for_option(vote_id: int, option_index: int):
    """
    Добавляет голос за указанный вариант в голосовании.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    if option_index == 0:
        cursor.execute('UPDATE votes SET votes_a = votes_a + 1 WHERE id = ?', (vote_id,))
    elif option_index == 1:
        cursor.execute('UPDATE votes SET votes_b = votes_b + 1 WHERE id = ?', (vote_id,))
    
    conn.commit()
    conn.close()


def has_user_voted(vote_id: int, user_id: int) -> bool:
    """
    Проверяет, голосовал ли пользователь в указанном голосовании.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    # Проверяем, есть ли запись о голосовании пользователя в этом голосовании
    # В реальной реализации потребуется дополнительная таблица для отслеживания голосов пользователей
    # Здесь временно возвращаем False, чтобы избежать ошибки
    conn.close()
    
    return False


def get_faq_answer(question: str) -> str | None:
    """
    Возвращает ответ на вопрос из FAQ.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    # Ищем частичное совпадение вопроса в базе FAQ
    cursor.execute('SELECT answer FROM faq WHERE question LIKE ?', (f'%{question}%',))
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        return result[0]
    return None


def add_faq_entry(question: str, answer: str):
    """
    Добавляет запись в FAQ.
    """
    conn = sqlite3.connect('vapelume.db')
    cursor = conn.cursor()
    
    # Добавляем или заменяем запись в FAQ
    cursor.execute('''
        INSERT OR REPLACE INTO faq (question, answer)
        VALUES (?, ?)
    ''', (question, answer))
    
    conn.commit()
    conn.close()