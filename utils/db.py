import psycopg2
import re
from config import DB_NAME, DB_USER, DB_PASSWORD, DB_HOST
from datetime import datetime, timedelta
import math

def connect_db():
    try:
        return psycopg2.connect(
            dbname=DB_NAME, 
            user=DB_USER, 
            password=DB_PASSWORD, 
            host=DB_HOST
        )
    except psycopg2.Error as e:
        print(f"Database connection error: {e}")
        raise

def sanitize_username(username):
    return username if re.match(r'^[a-zA-Z0-9]{1,20}$', username) else None

def user_exists(user_id):
    try:
        with connect_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 FROM users WHERE user_id = %s", (user_id,))
                return cursor.fetchone() is not None
    except psycopg2.Error as e:
        print(f"Error executing query: {e}")
        return False

def add_user(user_id, username):
    sanitized_username = sanitize_username(username)
    username = sanitized_username if sanitized_username else f"user{user_id}" if user_id else "unknown_user"

    try:
        with connect_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute(""" 
                    INSERT INTO users (user_id, username, balance, experience) 
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id) DO NOTHING;
                """, (user_id, username, 0, 0))
                conn.commit()
    except psycopg2.Error as e:
        print(f"Error executing query: {e}")

def get_user_data(user_id):
    try:
        with connect_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT username, balance, experience, started_working FROM users WHERE user_id = %s", (user_id,))
                return cursor.fetchone()
    except psycopg2.Error as e:
        print(f"Error executing query: {e}")
        return None

def update_username(user_id, new_username):
    sanitized_username = sanitize_username(new_username)
    if not sanitized_username:
        return False
    
    try:
        with connect_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE users SET username = %s WHERE user_id = %s", (sanitized_username, user_id))
                conn.commit()
    except psycopg2.Error as e:
        print(f"Error executing query: {e}")

def claim_daily_reward(user_id):
    today = datetime.now().date()
    
    try:
        with connect_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT last_claim_date FROM daily_rewards WHERE user_id = %s", (user_id,))
                result = cursor.fetchone()

                if result and result[0] == today:
                    return "Вы уже получили свою награду сегодня!"

                cursor.execute("SELECT experience FROM users WHERE user_id = %s", (user_id,))
                experience = cursor.fetchone()

                if experience:
                    level, _ = calculate_level(experience[0])
                    reward_edd = 5 + (level * 2)
                    reward_exp = 10 + (level * 5)
                else:
                    return "Пользователь не найден."

                cursor.execute("""
                    INSERT INTO daily_rewards (user_id, last_claim_date) 
                    VALUES (%s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET last_claim_date = EXCLUDED.last_claim_date;
                """, (user_id, today))

                cursor.execute("""
                    UPDATE users SET balance = balance + %s, experience = experience + %s WHERE user_id = %s;
                """, (reward_edd, reward_exp, user_id))

                conn.commit()
                return f"Поздравляем! Вы получили {reward_edd} евродолларов и {reward_exp} опыта."

    except psycopg2.Error as e:
        print(f"Error executing query: {e}")
        return "Произошла ошибка при получении награды."

def get_top_users_by_level(limit=10):
    try:
        with connect_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT username, experience FROM users 
                    ORDER BY experience DESC 
                    LIMIT %s;
                """, (limit,))
                return cursor.fetchall()
    except psycopg2.Error as e:
        print(f"Error executing query: {e}")
        return []

def get_top_users_by_cash(limit=10):
    try:
        with connect_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT username, balance FROM users 
                    ORDER BY balance DESC 
                    LIMIT %s;
                """, (limit,))
                return cursor.fetchall()
    except psycopg2.Error as e:
        print(f"Error executing query: {e}")
        return []

def get_user_job(user_id):
    user_data = get_user_data(user_id)
    if not user_data:
        return "unknown"

    experience = user_data[2]
    started_working = user_data[3]
    level, _ = calculate_level(experience)

    if started_working:
        work_duration = timedelta(hours=4)
        time_working = datetime.now() - started_working

        if time_working < work_duration:
            remaining_time = work_duration - time_working
            hours, remainder = divmod(remaining_time.seconds, 3600)
            minutes = math.ceil(remainder / 60)
            if minutes == 60:
                hours += 1
                minutes = 0
            return f"В работе: {get_job_name_by_level(level)}, осталось {hours}ч {minutes}мин"
        else:
            return get_job_name_by_level(level)

    return get_job_name_by_level(level)

def get_job_name_by_level(level):
    try:
        with connect_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT job_name FROM jobs WHERE required_level <= %s ORDER BY required_level DESC LIMIT 1", (level,))
                job = cursor.fetchone()
                return job[0] if job else "Безработный"
    except psycopg2.Error as e:
        print(f"Error executing query: {e}")
        return "Ошибка получения работы"

def calculate_level(experience):
    level = math.floor((15 + math.sqrt(225 + 60 * experience)) / 30)
    exp_for_next_lvl = 15 * ((level + 1) ** 2) - 15 * (level + 1)
    return level, exp_for_next_lvl

def set_started_working(user_id):
    start_time = datetime.now()
    try:
        with connect_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE users SET started_working = %s WHERE user_id = %s", (start_time, user_id))
                conn.commit()
    except psycopg2.Error as e:
        print(f"Error executing query: {e}")

def check_for_completed_work():
    try:
        with connect_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT user_id, started_working, experience, balance FROM users WHERE started_working IS NOT NULL")
                users = cursor.fetchall()

                for user in users:
                    user_id, started_working, experience, balance = user
                    work_duration = timedelta(hours=4)
                    time_working = datetime.now() - started_working

                    if time_working >= work_duration:
                        job_name, salary, experience_gain = get_job_info_by_user(user_id)

                        new_balance = balance + salary * 4
                        new_experience = experience + experience_gain * 4

                        cursor.execute("""
                            UPDATE users
                            SET balance = %s, experience = %s, started_working = NULL
                            WHERE user_id = %s
                        """, (new_balance, new_experience, user_id))

                conn.commit()

    except psycopg2.Error as e:
        print(f"Error checking for completed work: {e}")

def get_job_info_by_user(user_id):
    experience = get_user_data(user_id)[2]
    level, _ = calculate_level(experience)

    try:
        with connect_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT job_name, salary, experience FROM jobs WHERE required_level <= %s ORDER BY required_level DESC LIMIT 1", (level,))
                job = cursor.fetchone()
                return job[0], job[1], job[2] if job else ("unknown", 0, 0)
    except psycopg2.Error as e:
        print(f"Error executing query: {e}")
        return "unknown", 0, 0
