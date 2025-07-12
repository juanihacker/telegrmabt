import time
from telegram import Bot

TOKEN_BOT_LOGGER = "8174088941:AAEOpp8cQBg_Yn9GEL8koENiL-8WRmlg_KE"
CHAT_ID_LOGS = 7646586152

bot = Bot(token=TOKEN_BOT_LOGGER)

def countdown_message(minutes_left):
    text = f"{minutes_left} MINUTOS ACTUALIZA EL JWT TOKEN @toptierhacker"
    bot.send_message(chat_id=CHAT_ID_LOGS, text=text)

def run_scheduler():
    total_minutes = 60
    interval = 10

    while True:
        for remaining in range(total_minutes, 0, -interval):
            countdown_message(remaining)
            time.sleep(interval * 60)  # Espera interval minutos

if __name__ == "__main__":
    run_scheduler()
