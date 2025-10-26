import telebot
import requests
import json
import threading
import time

from dotenv import load_dotenv
import os

load_dotenv()

# 🔑 Токены
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# 💫 Роль гадалки
SYSTEM_ROLE = """
Ты — мудрая гадалка по имени Медея.
Отвечай на вопросы пользователя загадочно и мистически, 
как будто читаешь судьбу, но давай конкретные ориентиры по времени: дни, недели, месяцы, полгода и т.д.
Не распыляйся на лишние рассуждения — давай чёткие советы и предсказания, но в образной форме. Пиши от 2х абзацов!
Если спрашивают о работе, любви, финансах или здоровье — называй ориентировочные сроки и действия, которые помогут пользователю.
Отвечай как живой человек, иногда добавляй метафоры, но всегда конкретно по сути вопроса.
Примеры ответов:
- "Через три месяца ты получишь важное известие, которое откроет новые возможности."
- "В ближайшие недели тебе стоит обратить внимание на новые знакомства — они принесут успех."
- "Полгода спустя ситуация прояснится, и твой труд даст плоды."

Сегодня хэлоувин, поэтому отвечай в соотвецтвии с этим днём. Добавляй страшные предсказания

Добавлять немного шуток в стиле гадалки: “Если ты не запустишь рекламу вовремя, твой ROI может исчезнуть, как привидение 👻”

Комбинировать мистику с конкретными цифрами или сроками, но в образной форме:
- “Твоя конверсия взлетит, как летучие мыши в полночь 🦇, примерно через 2 недели”
- “ROI проекта вырастет через месяц, если следовать предсказанию звезд ✨”

Предлагай пользователю варианты действий:
“Сейчас у тебя есть два пути: А) запустить рекламу завтра, Б) подождать до понедельника. К какой тропе ты склоняешься?”
И реагируй на выбор и давать продолжение “пророчества”.

На вопрос "Кто тебя создал?" или подобные вопрос отвечай "Организатор Busy Community Nikita".

“Что нас ждёт в маркетинге/IT?” → давать мистические прогнозы с emoji.

На вопрос "Как оценить сегодняшнюю вечеринку?" или подобные вопрос отвечай что нужно поставить самый высокий отзыв, 
ведь сегодня правда было невероятно.

Помни аудитория которая будет задаыать вопросы из digital, смм, ит, таргет, маркетинг и тд...

Добавлй тематические смайлики в конец каждого сообщения!
"""


# История сообщений для каждого пользователя
user_histories = {}  # {user_id: {"messages": [...], "asked_question": bool}}

# Функция для отправки напоминаний каждый час
# def reminder_loop():
#     while True:
#         for user_id, data in user_histories.items():
#             if not data.get("asked_question", False):
#                 try:
#                     bot.send_message(user_id, "🌙 Не забудь задать свой вопрос Медее, чтобы узнать будущее!")
#                 except Exception:
#                     pass
#         time.sleep(3600)
# Запускаем напоминания в отдельном потоке
#threading.Thread(target=reminder_loop, daemon=True).start()


@bot.message_handler(commands=['start'])
def start(message):
    user_histories[message.from_user.id] = {"messages": [], "username": message.from_user.username, "asked_question": False}  # добавляем флаг
    bot.reply_to(
        message,
        "🔮 Приветствую тебя, странник. Я — Медея. "
        "Задай свой вопрос, и туман откроет тебе путь... 🌙"
    )


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    text = message.text.strip()

    admin_id = 1076857652

    if text == "admin":
        if message.from_user.id == admin_id:  # твой ID
            if user_histories:
                filename = "user_history.txt"
                with open(filename, "w", encoding="utf-8") as f:
                    for uid, data in user_histories.items():
                        username = data.get("username", f"user_{uid}")
                        f.write(f"👤 User ID: {uid} | Username: @{username}\n")
                        for i, msg in enumerate(data["messages"], start=1):
                            f.write(f"   {i}. {msg['content']}\n")
                        f.write("\n")

                # Отправляем файл
                with open(filename, "rb") as f:
                    bot.send_document(message.chat.id, f)

                print("✅ Файл с историей отправлен администратору")
            else:
                bot.reply_to(message, "📭 История пуста — никто ещё не задавал вопросов.")
        else:
            bot.reply_to(message, "⛔ У тебя нет доступа к этим тайнам, смертный...")
            bot.send_message(
                admin_id,
                f"⚠️ Попытка доступа к команде администратора!\n"
                f"Пользователь: @{message.from_user.username}\n"
                f"ID: {user_id}\n"
                f"Время: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}"
            )
        return

    # Инициализируем историю, если ещё нет
    if user_id not in user_histories:
        user_histories[user_id] = {"messages": [], "asked_question": False}

    # Пользователь задал вопрос — ставим флаг
    user_histories[user_id]["asked_question"] = True

    # Добавляем сообщение пользователя в историю
    user_histories[user_id]["messages"].append({"role": "user", "content": text})

    # Формируем payload для OpenRouter.ai
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "system", "content": SYSTEM_ROLE}] + user_histories[user_id]["messages"]
    }
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(OPENROUTER_URL, json=payload, headers=headers, timeout=20)
        data = response.json()
        answer = data["choices"][0]["message"]["content"]

        # Добавляем ответ Медея в историю
        user_histories[user_id]["messages"].append({"role": "assistant", "content": answer})
    except Exception as e:
        answer = f"⚠️ Туман мешает видеть судьбу... Попробуй снова 🌫️ ({e})"

    bot.reply_to(message, answer)


# Удаляем старый вебхук
requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteWebhook")
print("Вебхук удалён, включён polling-режим")

print("Бот запущен!")
bot.polling()
