from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from handlers.message_handler import handle_message, set_name, profile, claim_reward, work, top_level, top_cash
from utils.db import check_for_completed_work
from config import TOKEN
from apscheduler.schedulers.asyncio import AsyncIOScheduler

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler('profile', profile))
    app.add_handler(CommandHandler('work', work))
    app.add_handler(CommandHandler('setname', set_name))
    app.add_handler(CommandHandler('claimreward', claim_reward))
    app.add_handler(CommandHandler("toplvl", top_level))
    app.add_handler(CommandHandler("topcash", top_cash))

    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_for_completed_work, 'interval', minutes=1)
    scheduler.start()

    app.run_polling()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Bot stopped.")
