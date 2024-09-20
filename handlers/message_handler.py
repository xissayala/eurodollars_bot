import psycopg2
from telegram import Update
from telegram.ext import ContextTypes
from utils.db import (
    add_user,
    user_exists,
    update_username,
    get_user_data,
    sanitize_username,
    claim_daily_reward,
    calculate_level,
    set_started_working,
    get_user_job,
    check_for_completed_work,
    get_top_users_by_level,
    get_top_users_by_cash,
)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    check_for_completed_work()
    
    username = sanitize_username(user.username)
    if not user_exists(user_id):
        username = username or f"user{user_id}"
        add_user(user_id, username)
        await update.message.reply_text(
            f"Привет, {username}! 🎉 Добро пожаловать в Eddies - Ваш Euro Dollar Bot! 🌟"
            " Мы рады видеть вас здесь. Каждый день и каждую неделю вас ждут отличные награды! "
            "Не забудьте проверять свои достижения и получать бонусы!"
        )

async def top_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    check_for_completed_work()
    user_id = update.message.from_user.id
    
    if not user_exists(user_id):
        await handle_message(update, context)
        return

    top_users = get_top_users_by_level()
    message = "🏆 Топ 10 по уровням:\n"
    for username, experience in top_users:
        level, _ = calculate_level(experience)
        message += f"{username} - Уровень: {level}\n"
    await update.message.reply_text(message)

async def top_cash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    check_for_completed_work()
    user_id = update.message.from_user.id
    
    if not user_exists(user_id):
        await handle_message(update, context)
        return

    top_users = get_top_users_by_cash()
    message = "💰 Топ 10 по балансу:\n"
    for username, balance in top_users:
        message += f"{username} - Баланс: {balance} евродолларов\n"
    await update.message.reply_text(message)

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    check_for_completed_work()
    
    if not user_exists(user_id):
        await handle_message(update, context)
        return

    user_data = get_user_data(user_id)
    job = get_user_job(user_id)
    
    if user_data:
        username, balance, experience = user_data[:3]
    else:
        username, balance, experience = 'unknown', 'unknown', 0

    level, exp_for_next_lvl = calculate_level(experience)
    
    await update.message.reply_text(
        f"Имя: {username} 🎭\nБаланс: {balance} 💰\nОпыт: {experience}/{exp_for_next_lvl} 📈\nУровень: {level} 🏆\nРабота: {job} 🛠️"
    )

async def work(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user_data(user_id)
    check_for_completed_work()

    if not user_exists(user_id):
        await handle_message(update, context)
        return

    if user_data[3] is not None:
        await update.message.reply_text("Вы уже на работе!")
        return

    await update.message.reply_text("Вы отправлены на работу!")
    set_started_working(user_id)

async def set_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    check_for_completed_work()
    
    if not user_exists(user_id):
        await handle_message(update, context)
        return
    
    if context.args:
        new_name = " ".join(context.args)
        sanitized_name = sanitize_username(new_name)

        if not sanitized_name:
            return await update.message.reply_text("Используйте только латиницу и цифры и не превышайте 15 символов.")

        update_username(user_id, sanitized_name)
        await update.message.reply_text(f"Ваше имя изменено на: {sanitized_name}")
    else:
        await update.message.reply_text("Пожалуйста, укажите новое имя.")

async def claim_reward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    check_for_completed_work()
    user_id = update.message.from_user.id
    
    if not user_exists(user_id):
        await handle_message(update, context)
        return
    
    message = claim_daily_reward(user_id)
    await update.message.reply_text(message)
