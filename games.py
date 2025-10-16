import random
import asyncio
from telegram import Update
from telegram.ext import ContextTypes, Application
from database import get_user_balance, update_user_balance, get_game_setting

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


async def delete_message_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int):
    """
    Удаляет сообщение через заданное количество секунд
    """
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass  # Сообщение могло быть уже удалено


@group_only
async def roulette(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Игра в рулетку
    /roulette [ставка]
    Ставка ≥ 25 LumeCoin.
    30% шанс на выигрыш (x2), остальное — проигрыш.
    Анимация: 🎰 → 🔴/⚫️/🟢 → результат.
    """
    user_id = update.effective_user.id
    
    # Проверяем аргументы
    if not context.args or len(context.args) != 1:
        message = await update.message.reply_text('❌ Укажите ставку: /roulette <ставка>')
        context.application.job_queue.run_once(
            lambda _: delete_message_after_delay(context, update.effective_chat.id, message.id, 300),
            when=300
        )
        return
    
    try:
        bet = float(context.args[0])
        if bet < 25:
            message = await update.message.reply_text('❌ Минимальная ставка 25 LumeCoin')
            context.application.job_queue.run_once(
                lambda _: delete_message_after_delay(context, update.effective_chat.id, message.id, 300),
                when=300
            )
            return
    except ValueError:
        message = await update.message.reply_text('❌ Некорректная ставка. Укажите число: /roulette <ставка>')
        context.application.job_queue.run_once(
            lambda _: delete_message_after_delay(context, update.effective_chat.id, message.id, 300),
            when=300
        )
        return
    
    # Проверяем баланс
    balance = get_user_balance(user_id)
    if balance < bet:
        message = await update.message.reply_text(f'❌ Недостаточно средств. Ваш баланс: {balance:.1f} LumeCoin')
        context.application.job_queue.run_once(
            lambda _: delete_message_after_delay(context, update.effective_chat.id, message.id, 300),
            when=300
        )
        return
    
    # Снимаем ставку
    update_user_balance(user_id, -bet)
    
    # Анимация: 🎰
    msg = await update.message.reply_text('🎰')
    await asyncio.sleep(1)
    
    # Определяем результат
    result = random.choices(['win', 'lose'], weights=[30, 70])[0]
    
    if result == 'win':
        # Выигрыш (x2)
        win_amount = bet * 2
        update_user_balance(user_id, win_amount)
        # Анимация: 🔴/⚫️/🟢 (в зависимости от числа)
        color = random.choice(['🔴', '⚫️', '🟢'])
        await msg.edit_text(f'{color}')
        await asyncio.sleep(1)
        await msg.edit_text(f'🎉 Поздравляем! Вы выиграли {win_amount:.1f} LumeCoin!')
    else:
        # Проигрыш
        # Анимация: 🔴/⚫️/🟢 (в зависимости от числа)
        color = random.choice(['🔴', '⚫️', '🟢'])
        await msg.edit_text(f'{color}')
        await asyncio.sleep(1)
        await msg.edit_text(f'😔 Вы проиграли {bet:.1f} LumeCoin.')
    
    # Обновляем баланс и отправляем финальное сообщение
    new_balance = get_user_balance(user_id)
    final_msg = await update.message.reply_text(f'💰 Ваш баланс: {new_balance:.1f} LumeCoin')
    
    # Удаляем сообщения через 5 минут
    context.application.job_queue.run_once(
        lambda _: delete_message_after_delay(context, update.effective_chat.id, update.message.id, 300),
        when=300
    )
    context.application.job_queue.run_once(
        lambda _: delete_message_after_delay(context, update.effective_chat.id, msg.id, 300),
        when=300
    )
    context.application.job_queue.run_once(
        lambda _: delete_message_after_delay(context, update.effective_chat.id, final_msg.id, 300),
        when=300
    )


@group_only
async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Игра в кости
    /play
    Фиксированная ставка 25 LumeCoin.
    40% шанс выиграть 40 LumeCoin.
    Анимация: 🎲 → ... → результат.
    """
    user_id = update.effective_user.id
    bet = 25
    
    # Проверяем баланс
    balance = get_user_balance(user_id)
    if balance < bet:
        message = await update.message.reply_text(f'❌ Недостаточно средств. Ваш баланс: {balance:.1f} LumeCoin')
        context.application.job_queue.run_once(
            lambda _: delete_message_after_delay(context, update.effective_chat.id, message.id, 300),
            when=300
        )
        return
    
    # Снимаем ставку
    update_user_balance(user_id, -bet)
    
    # Анимация: 🎲
    msg = await update.message.reply_text('🎲')
    await asyncio.sleep(2)
    
    # Определяем результат
    result = random.choices(['win', 'lose'], weights=[40, 60])[0]
    
    if result == 'win':
        # Выигрыш 40 LumeCoin
        win_amount = 40
        update_user_balance(user_id, win_amount)
        await msg.edit_text(f'🎉 Поздравляем! Вы выиграли {win_amount:.1f} LumeCoin!')
    else:
        # Проигрыш
        await msg.edit_text(f'😔 Вы проиграли {bet:.1f} LumeCoin.')
    
    # Обновляем баланс и отправляем финальное сообщение
    new_balance = get_user_balance(user_id)
    final_msg = await update.message.reply_text(f'💰 Ваш баланс: {new_balance:.1f} LumeCoin')
    
    # Удаляем сообщения через 5 минут
    context.application.job_queue.run_once(
        lambda _: delete_message_after_delay(context, update.effective_chat.id, update.message.id, 300),
        when=300
    )
    context.application.job_queue.run_once(
        lambda _: delete_message_after_delay(context, update.effective_chat.id, msg.id, 300),
        when=300
    )
    context.application.job_queue.run_once(
        lambda _: delete_message_after_delay(context, update.effective_chat.id, final_msg.id, 300),
        when=300
    )


@group_only
async def russian(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Русская рулетка
    /russian
    Бесплатно.
    65% шанс: мут на 5 минут (context.bot.restrict_chat_member).
    35% шанс: выигрыш 35 LumeCoin.
    Анимация: 🔫 → ... → 💥/💰.
    """
    user_id = update.effective_user.id
    
    # Анимация: 🔫
    msg = await update.message.reply_text('🔫')
    await asyncio.sleep(2)
    
    # Определяем результат
    result = random.choices(['lose', 'win'], weights=[65, 35])[0]
    
    if result == 'lose':
        # Мут на 5 минут
        from datetime import datetime, timedelta
        mute_until = datetime.now() + timedelta(minutes=5)
        try:
            await context.bot.restrict_chat_member(
                chat_id=update.effective_chat.id,
                user_id=user_id,
                permissions=context.bot.get_chat(update.effective_chat.id).permissions,
                until_date=mute_until
            )
            await msg.edit_text(f'💥 Вы проиграли! Мут на 5 минут.')
        except Exception:
            await msg.edit_text(f'💥 Вы проиграли! (Не удалось выдать мут)')
    else:
        # Выигрыш 35 LumeCoin
        win_amount = 35
        update_user_balance(user_id, win_amount)
        await msg.edit_text(f'💰 Поздравляем! Вы выиграли {win_amount:.1f} LumeCoin!')
    
    # Обновляем баланс и отправляем финальное сообщение
    new_balance = get_user_balance(user_id)
    final_msg = await update.message.reply_text(f'💰 Ваш баланс: {new_balance:.1f} LumeCoin')
    
    # Удаляем сообщения через 5 минут
    context.application.job_queue.run_once(
        lambda _: delete_message_after_delay(context, update.effective_chat.id, update.message.id, 300),
        when=300
    )
    context.application.job_queue.run_once(
        lambda _: delete_message_after_delay(context, update.effective_chat.id, msg.id, 300),
        when=300
    )
    context.application.job_queue.run_once(
        lambda _: delete_message_after_delay(context, update.effective_chat.id, final_msg.id, 300),
        when=300
    )


@group_only
async def jewish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Еврейская рулетка
    /jewish
    Бесплатно.
    50% шанс: проигрыш 35 LumeCoin.
    50% шанс: выигрыш 25 LumeCoin.
    Анимация: ✡️ → ... → 💸/🤑.
    """
    user_id = update.effective_user.id
    
    # Анимация: ✡️
    msg = await update.message.reply_text('✡️')
    await asyncio.sleep(2)
    
    # Определяем результат
    result = random.choices(['lose', 'win'], weights=[50, 50])[0]
    
    if result == 'lose':
        # Проигрыш 35 LumeCoin
        loss_amount = 35
        balance = get_user_balance(user_id)
        if balance >= loss_amount:
            update_user_balance(user_id, -loss_amount)
            await msg.edit_text(f'💸 Вы проиграли {loss_amount:.1f} LumeCoin.')
        else:
            # Если баланс меньше, проигрываем всю сумму
            update_user_balance(user_id, -balance)
            await msg.edit_text(f'💸 Вы проиграли {balance:.1f} LumeCoin.')
    else:
        # Выигрыш 25 LumeCoin
        win_amount = 25
        update_user_balance(user_id, win_amount)
        await msg.edit_text(f'🤑 Поздравляем! Вы выиграли {win_amount:.1f} LumeCoin!')
    
    # Обновляем баланс и отправляем финальное сообщение
    new_balance = get_user_balance(user_id)
    final_msg = await update.message.reply_text(f'💰 Ваш баланс: {new_balance:.1f} LumeCoin')
    
    # Удаляем сообщения через 5 минут
    context.application.job_queue.run_once(
        lambda _: delete_message_after_delay(context, update.effective_chat.id, update.message.id, 300),
        when=300
    )
    context.application.job_queue.run_once(
        lambda _: delete_message_after_delay(context, update.effective_chat.id, msg.id, 300),
        when=300
    )
    context.application.job_queue.run_once(
        lambda _: delete_message_after_delay(context, update.effective_chat.id, final_msg.id, 300),
        when=300
    )


@group_only
async def dice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Игра в кости с Telegram-анимацией
    /dice [ставка]
    Ставка от 10 до 100 LumeCoin.
    Игрок бросает кубик (context.bot.send_dice).
    Если выпало значение ≥ 4, выигрыш x1.5.
    """
    user_id = update.effective_user.id
    
    # Проверяем аргументы
    if not context.args or len(context.args) != 1:
        message = await update.message.reply_text('❌ Укажите ставку: /dice <ставка>')
        context.application.job_queue.run_once(
            lambda _: delete_message_after_delay(context, update.effective_chat.id, message.id, 300),
            when=300
        )
        return
    
    try:
        bet = float(context.args[0])
        if bet < 10 or bet > 100:
            message = await update.message.reply_text('❌ Ставка должна быть от 10 до 100 LumeCoin')
            context.application.job_queue.run_once(
                lambda _: delete_message_after_delay(context, update.effective_chat.id, message.id, 300),
                when=300
            )
            return
    except ValueError:
        message = await update.message.reply_text('❌ Некорректная ставка. Укажите число: /dice <ставка>')
        context.application.job_queue.run_once(
            lambda _: delete_message_after_delay(context, update.effective_chat.id, message.id, 300),
            when=300
        )
        return
    
    # Проверяем баланс
    balance = get_user_balance(user_id)
    if balance < bet:
        message = await update.message.reply_text(f'❌ Недостаточно средств. Ваш баланс: {balance:.1f} LumeCoin')
        context.application.job_queue.run_once(
            lambda _: delete_message_after_delay(context, update.effective_chat.id, message.id, 300),
            when=300
        )
        return
    
    # Снимаем ставку
    update_user_balance(user_id, -bet)
    
    # Бросаем кубик
    dice_msg = await context.bot.send_dice(chat_id=update.effective_chat.id, message_thread_id=update.message.message_thread_id if update.message.is_topic_message else None)
    dice_value = dice_msg.dice.value
    
    await asyncio.sleep(3)  # Ждем завершения анимации кубика
    
    # Определяем результат
    if dice_value >= 4:
        # Выигрыш x1.5
        win_amount = bet * 1.5
        update_user_balance(user_id, win_amount)
        result_msg = await update.message.reply_text(f'🎉 Поздравляем! Вы выиграли {win_amount:.1f} LumeCoin!')
    else:
        # Проигрыш
        result_msg = await update.message.reply_text(f'😔 Вы проиграли {bet:.1f} LumeCoin.')
    
    # Обновляем баланс и отправляем финальное сообщение
    new_balance = get_user_balance(user_id)
    final_msg = await update.message.reply_text(f'💰 Ваш баланс: {new_balance:.1f} LumeCoin')
    
    # Удаляем сообщения через 5 минут
    context.application.job_queue.run_once(
        lambda _: delete_message_after_delay(context, update.effective_chat.id, update.message.id, 300),
        when=300
    )
    context.application.job_queue.run_once(
        lambda _: delete_message_after_delay(context, update.effective_chat.id, dice_msg.id, 300),
        when=300
    )
    context.application.job_queue.run_once(
        lambda _: delete_message_after_delay(context, update.effective_chat.id, result_msg.id, 300),
        when=300
    )
    context.application.job_queue.run_once(
        lambda _: delete_message_after_delay(context, update.effective_chat.id, final_msg.id, 300),
        when=300
    )


@group_only
async def slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Игра в слоты
    /slots
    Фиксированная ставка 50 LumeCoin.
    Использует context.bot.send_dice(emoji="🎰").
    Логика выигрыша на основе dice.value (значения от 1 до 64). 
    Определяет комбинации для 3 и 2 совпадений.
    3 совпадения: выигрыш x5.
    2 совпадения: выигрыш x2.
    """
    user_id = update.effective_user.id
    bet = 50
    
    # Проверяем баланс
    balance = get_user_balance(user_id)
    if balance < bet:
        message = await update.message.reply_text(f'❌ Недостаточно средств. Ваш баланс: {balance:.1f} LumeCoin')
        context.application.job_queue.run_once(
            lambda _: delete_message_after_delay(context, update.effective_chat.id, message.id, 300),
            when=300
        )
        return
    
    # Снимаем ставку
    update_user_balance(user_id, -bet)
    
    # Бросаем слоты
    dice_msg = await context.bot.send_dice(chat_id=update.effective_chat.id, emoji="🎰", message_thread_id=update.message.message_thread_id if update.message.is_topic_message else None)
    dice_value = dice_msg.dice.value
    
    await asyncio.sleep(3)  # Ждем завершения анимации
    
    # Определяем выигрыш на основе значения кубика
    # В Telegram слотах значения от 1 до 64:
    # 1 - 3 совпадения (якобы джекпот)
    # 2-7 - 2 совпадения
    # 8-64 - проигрыш
    
    if dice_value == 1:
        # Джекпот - 3 совпадения
        win_amount = bet * 5
        update_user_balance(user_id, win_amount)
        result_msg = await update.message.reply_text(f'🎰🎉 Джекпот! Вы выиграли {win_amount:.1f} LumeCoin!')
    elif 2 <= dice_value <= 7:
        # 2 совпадения
        win_amount = bet * 2
        update_user_balance(user_id, win_amount)
        result_msg = await update.message.reply_text(f'🎰💰 2 совпадения! Вы выиграли {win_amount:.1f} LumeCoin!')
    else:
        # Проигрыш
        result_msg = await update.message.reply_text(f'🎰😔 Вы проиграли {bet:.1f} LumeCoin.')
    
    # Обновляем баланс и отправляем финальное сообщение
    new_balance = get_user_balance(user_id)
    final_msg = await update.message.reply_text(f'💰 Ваш баланс: {new_balance:.1f} LumeCoin')
    
    # Удаляем сообщения через 5 минут
    context.application.job_queue.run_once(
        lambda _: delete_message_after_delay(context, update.effective_chat.id, update.message.id, 300),
        when=300
    )
    context.application.job_queue.run_once(
        lambda _: delete_message_after_delay(context, update.effective_chat.id, dice_msg.id, 300),
        when=300
    )
    context.application.job_queue.run_once(
        lambda _: delete_message_after_delay(context, update.effective_chat.id, result_msg.id, 300),
        when=300
    )
    context.application.job_queue.run_once(
        lambda _: delete_message_after_delay(context, update.effective_chat.id, final_msg.id, 300),
        when=300
    )