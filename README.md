# Бот отслеживания скидок на игры

Телеграм-бот, который отслеживает скидки на игры в различных цифровых магазинах и уведомляет пользователей о снижении цен.

## Возможности

- 🔍 Поиск игр по названию
- 📊 Отслеживание цен на игры в разных магазинах
- 🔔 Уведомления о снижении цен
- 📱 Управление подписками через Telegram
- 🌐 Веб-интерфейс для управления ботом

## Технологии

- Python 3.11
- Flask (веб-интерфейс)
- python-telegram-bot (Telegram API)
- SQLAlchemy (работа с базой данных)
- PostgreSQL (база данных)
- APScheduler (планировщик задач)

## Установка и запуск

1. Клонировать репозиторий:
   ```
   git clone https://github.com/ваш-логин/game-discount-tracker-bot.git
   cd game-discount-tracker-bot
   ```

2. Установить зависимости:
   ```
   pip install -r requirements.txt
   ```

3. Настроить переменные окружения:
   - `TELEGRAM_TOKEN` - токен Telegram бота (получить у [@BotFather](https://t.me/BotFather))
   - `DATABASE_URL` - URL подключения к PostgreSQL

4. Запустить приложение:
   ```
   python main.py
   ```

## Использование

1. Найдите бота в Telegram
2. Используйте команду `/search <название_игры>` для поиска игр
3. Подпишитесь на уведомления с помощью команды `/subscribe <id_игры>`
4. Получайте уведомления о снижении цены на выбранные игры
5. Управляйте подписками с помощью команды `/mysubs`

## Команды бота

- `/start` - Начать работу с ботом
- `/help` - Показать справку
- `/search <название_игры>` - Поиск игр
- `/subscribe <id_игры>` - Подписаться на уведомления
- `/unsubscribe <id_игры>` - Отписаться от уведомлений
- `/mysubs` - Просмотр ваших подписок
- `/discounts` - Показать текущие скидки

## Лицензия

MIT