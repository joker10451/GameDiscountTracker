import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.game_service import search_game, get_game_details, get_similar_games, get_price_history
from services.price_tracker import get_current_discounts
from data.data_manager import add_subscription, remove_subscription, get_user_subscriptions, update_user_info
from flask import current_app

# Set up logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение при команде /start."""
    user = update.effective_user

    # Сохранение информации о пользователе в базу данных
    with current_app.app_context():
        try:
            update_user_info(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            logger.info(f"Данные пользователя сохранены в базу данных: {user.id}")
        except Exception as e:
            logger.error(f"Ошибка сохранения данных пользователя: {e}")

    await update.message.reply_html(
        f"🎮 Привет, {user.mention_html()}! 👋\n\n"
        "Я твой персональный помощник по поиску скидок на игры!\n\n"
        "🔍 Что я умею:\n"
        "• Искать игры по названию, жанру или издателю\n"
        "• Отслеживать цены на твои любимые игры\n"
        "• Уведомлять о снижении цен\n"
        "• Показывать историю цен\n"
        "• Находить похожие игры\n\n"
        "📝 Используй /help для просмотра всех команд\n"
        "🎯 Начни с команды /search для поиска игр"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет сообщение при команде /help."""
    help_text = (
        "🎮 Доступные команды:\n\n"
        "🔍 Поиск:\n"
        "• /search <название> - Поиск игры\n"
        "• /search genre <жанр> - Поиск по жанру\n"
        "• /search publisher <издатель> - Поиск по издателю\n"
        "• /similar <id> - Найти похожие игры\n\n"
        "💰 Цены и скидки:\n"
        "• /history <id> - История цен\n"
        "• /discounts - Текущие скидки\n"
        "• /filter price <цена> - Фильтр по цене\n"
        "• /filter discount <процент> - Фильтр по скидке\n"
        "• /filter clear - Сбросить фильтры\n\n"
        "📋 Подписки:\n"
        "• /subscribe <id> - Подписаться на игру\n"
        "• /unsubscribe <id> - Отписаться от игры\n"
        "• /mysubs - Мои подписки\n\n"
        "❓ /help - Показать это сообщение"
    )
    await update.message.reply_text(help_text)

async def search_games(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ищет игры при команде /search."""
    if not context.args:
        await update.message.reply_text(
            "Используйте следующие команды для поиска:\n"
            "/search <название> - Поиск по названию\n"
            "/search genre <жанр> <название> - Поиск по жанру\n"
            "/search publisher <издатель> <название> - Поиск по издателю\n"
            "/similar <id_игры> - Поиск похожих игр\n"
            "/history <id_игры> - История цен"
        )
        return

    query = ' '.join(context.args)
    await update.message.reply_text(f"Ищу: {query}...")

    try:
        results = await search_game(query)

        if not results:
            await update.message.reply_text(f"Не найдено игр по запросу '{query}'. Попробуйте другой поисковый запрос.")
            return

        # Создает ответ с кнопками для каждого результата
        reply_text = "🎮 Результаты поиска:\n\n"
        keyboard = []

        for idx, game in enumerate(results[:5]):  # Ограничение до 5 результатов, чтобы избежать ограничения размера сообщения
            game_id = game.get('id')
            game_name = game.get('name')

            reply_text += f"{idx+1}. {game_name} (ID: {game_id})\n"

            # Добавляет кнопку для подписки и просмотра подробностей
            keyboard.append([
                InlineKeyboardButton(f"Подписаться на {game_name}", callback_data=f"sub_{game_id}"),
                InlineKeyboardButton(f"Подробности", callback_data=f"details_{game_id}")
            ])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(reply_text, reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Ошибка в search_games: {e}")
        await update.message.reply_text(f"Извините, произошла ошибка при поиске. Пожалуйста, попробуйте позже.")

async def subscribe_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Подписывает на оповещения о цене игры."""
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите ID игры, на которую хотите подписаться. Используйте /search для поиска ID игр.")
        return

    game_id = context.args[0]
    user_id = update.effective_user.id

    try:
        # Получает подробности об игре, чтобы проверить ее существование
        game_details = await get_game_details(game_id)

        if not game_details:
            await update.message.reply_text(f"Игра с ID {game_id} не найдена. Пожалуйста, проверьте ID и попробуйте снова.")
            return

        # Добавляет подписку в контексте приложения
        with current_app.app_context():
            # Получает миниатюру, если доступна
            thumbnail = game_details.get('thumbnail', None)
            success = add_subscription(user_id, game_id, game_details.get('name', 'Unknown Game'), thumbnail)

            if success:
                await update.message.reply_text(
                    f"✅ Вы подписались на уведомления о цене для игры {game_details.get('name')}.\n"
                    f"Я уведомлю вас, когда цена снизится!"
                )
            else:
                await update.message.reply_text(f"Вы уже подписаны на эту игру.")

    except Exception as e:
        logger.error(f"Ошибка в subscribe_game: {e}")
        await update.message.reply_text("Извините, произошла ошибка при подписке. Пожалуйста, попробуйте позже.")

async def unsubscribe_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отписывает от оповещений о цене игры."""
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите ID игры, от которой хотите отписаться. Используйте /mysubs, чтобы увидеть ваши подписки.")
        return

    game_id = context.args[0]
    user_id = update.effective_user.id

    try:
        # Удаляет подписку в контексте приложения
        with current_app.app_context():
            success, game_name = remove_subscription(user_id, game_id)

            if success:
                await update.message.reply_text(f"✅ Вы отписались от уведомлений о цене для игры {game_name}.")
            else:
                await update.message.reply_text("Вы не подписаны на эту игру.")

    except Exception as e:
        logger.error(f"Ошибка в unsubscribe_game: {e}")
        await update.message.reply_text("Извините, произошла ошибка при отписке. Пожалуйста, попробуйте позже.")

async def list_subscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает все игры, на которые подписан пользователь."""
    user_id = update.effective_user.id

    try:
        # Получает подписки в контексте приложения
        with current_app.app_context():
            subscriptions = get_user_subscriptions(user_id)

            if not subscriptions:
                await update.message.reply_text(
                    "У вас пока нет подписок на игры.\n"
                    "Используйте /search для поиска игр и подписки на них!"
                )
                return

            reply_text = "🎮 Ваши подписки на игры:\n\n"
            keyboard = []

            for game_id, game_info in subscriptions.items():
                game_name = game_info.get('name', 'Unknown Game')
                reply_text += f"• {game_name} (ID: {game_id})\n"

                # Добавляет кнопку для отписки
                keyboard.append([
                    InlineKeyboardButton(f"Отписаться от {game_name}", callback_data=f"unsub_{game_id}")
                ])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(reply_text, reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Ошибка в list_subscriptions: {e}")
        await update.message.reply_text("Извините, произошла ошибка при получении ваших подписок. Пожалуйста, попробуйте позже.")

async def check_discounts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает текущие скидки на игры."""
    progress_msg = await update.message.reply_text("🔍 Ищу лучшие предложения для вас...")

    try:
        max_price = context.user_data.get('max_price')
        min_discount = context.user_data.get('min_discount')

        discounts = await get_current_discounts(
            max_price=max_price,
            min_discount=min_discount
        )

        if not discounts:
            await progress_msg.edit_text("😔 Сейчас нет интересных скидок.\n\n💡 Включите уведомления (/mysubs), чтобы не пропустить выгодные предложения!")
            return

        reply_text = "🌟 ЛУЧШИЕ ПРЕДЛОЖЕНИЯ СЕГОДНЯ 🌟\n\n"
        keyboard = []

        for game in discounts[:10]:
            game_id = game.get('id')
            game_name = game.get('name')
            discount = game.get('discount_percent', 0)
            current_price = game.get('price_current', 'Неизвестно')
            original_price = game.get('price_original', 'Неизвестно')
            store = game.get('store', 'Неизвестный магазин')

            # Добавляем звездочки для больших скидок
            discount_stars = "⭐️" * (discount // 25) if discount >= 25 else ""

            reply_text += (
                f"〔 {game_name} 〕{discount_stars}\n"
                f"┌ 💰 Сейчас: {current_price}\n"
                f"├ 📈 Было: {original_price}\n"
                f"├ 🔥 Скидка: -{discount}%\n"
                f"└ 🏪 Магазин: {store}\n\n"
            )

            # Добавляет кнопку для подписки
            keyboard.append([
                InlineKeyboardButton(f"Подписаться на {game_name}", callback_data=f"sub_{game_id}"),
                InlineKeyboardButton(f"Подробности", callback_data=f"details_{game_id}")
            ])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await progress_msg.edit_text(reply_text, reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Ошибка в check_discounts: {e}")
        await progress_msg.edit_text("Извините, произошла ошибка при получении текущих скидок. Пожалуйста, попробуйте позже.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатия кнопок из инлайн-клавиатур."""
    query = update.callback_query
    await query.answer()

    data = query.data

    try:
        if data.startswith('sub_'):
            game_id = data[4:]
            user_id = update.effective_user.id

            # Получает подробности об игре
            game_details = await get_game_details(game_id)

            if not game_details:
                await query.edit_message_text(text=f"Игра с ID {game_id} не найдена. Пожалуйста, попробуйте другую игру.")
                return

            # Добавляет подписку в контексте приложения
            with current_app.app_context():
                # Получает миниатюру, если доступна
                thumbnail = game_details.get('thumbnail', None)
                success = add_subscription(user_id, game_id, game_details.get('name', 'Неизвестная игра'), thumbnail)

                if success:
                    await query.edit_message_text(
                        text=f"✅ Вы подписались на уведомления о цене для игры {game_details.get('name')}.\n"
                             f"Я уведомлю вас, когда цена снизится!"
                    )
                else:
                    await query.edit_message_text(text=f"Вы уже подписаны на эту игру.")

        elif data.startswith('unsub_'):
            game_id = data[6:]
            user_id = update.effective_user.id

            # Удаляет подписку в контексте приложения
            with current_app.app_context():
                success, game_name = remove_subscription(user_id, game_id)

                if success:
                    await query.edit_message_text(text=f"✅ Вы отписались от уведомлений о цене для игры {game_name}.")
                else:
                    await query.edit_message_text(text="Вы не подписаны на эту игру.")

        elif data.startswith('details_'):
            game_id = data[8:]

            # Получает подробности об игре
            game_details = await get_game_details(game_id)

            if not game_details:
                await query.edit_message_text(text=f"Игра с ID {game_id} не найдена. Пожалуйста, попробуйте другую игру.")
                return

            # Форматирует сообщение с подробными сведениями об игре
            game_name = game_details.get('name', 'Неизвестная игра')
            stores = game_details.get('stores', [])
            prices = game_details.get('prices', {})

            details_text = f"🎮 {game_name}\n\n"

            if 'description' in game_details:
                # Укорачивает описание, если оно слишком длинное
                description = game_details['description']
                if len(description) > 200:
                    description = description[:197] + "..."
                details_text += f"📝 {description}\n\n"

            details_text += "💰 Цены:\n"

            for store_name, price_info in prices.items():
                current_price = price_info.get('current', 'Неизвестно')
                original_price = price_info.get('original', 'Неизвестно')
                discount = price_info.get('discount_percent', 0)

                if discount > 0:
                    details_text += f"🏪 {store_name}: {current_price} (было {original_price}, -{discount}%)\n"
                else:
                    details_text += f"🏪 {store_name}: {current_price}\n"

            # Добавляет кнопку для подписки
            keyboard = [[InlineKeyboardButton(f"Подписаться на {game_name}", callback_data=f"sub_{game_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(text=details_text, reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Ошибка в button_handler: {e}")
        await query.edit_message_text(text="Извините, произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Логирует ошибки, вызванные обновлениями."""
    logger.error(f"Обновление {update} вызвало ошибку {context.error}")

    # Уведомляет пользователя об ошибке
    if update.effective_message:
        await update.effective_message.reply_text("Извините, что-то пошло не так. Пожалуйста, попробуйте позже.")


async def handle_filters(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает фильтры по цене и скидке"""
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "Используйте:\n"
            "/filter price <макс_цена> - Установить максимальную цену\n"
            "/filter discount <процент> - Установить минимальную скидку\n"
            "/filter clear - Сбросить фильтры"
        )
        return

    filter_type = context.args[0].lower()

    if filter_type == "clear":
        context.user_data.clear()
        await update.message.reply_text("✅ Все фильтры сброшены")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Пожалуйста, укажите значение для фильтра")
        return

    try:
        value = float(context.args[1])
        if filter_type == "price":
            if value <= 0:
                await update.message.reply_text("Цена должна быть больше 0")
                return
            context.user_data['max_price'] = value
            await update.message.reply_text(f"✅ Установлен фильтр по цене: до ${value:.2f}")

        elif filter_type == "discount":
            if not 0 <= value <= 100:
                await update.message.reply_text("Скидка должна быть от 0 до 100%")
                return
            context.user_data['min_discount'] = value
            await update.message.reply_text(f"✅ Установлен фильтр по скидке: от {value}%")

        else:
            await update.message.reply_text("Неизвестный тип фильтра. Используйте 'price' или 'discount'")

    except ValueError:
        await update.message.reply_text("Пожалуйста, укажите числовое значение")
async def similar_games(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает похожие игры."""
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите ID игры для поиска похожих. Пример: /similar 12345")
        return

    game_id = context.args[0]
    await update.message.reply_text("Ищу похожие игры...")

    try:
        similar = await get_similar_games(game_id)

        if not similar:
            await update.message.reply_text("Не удалось найти похожие игры.")
            return

        reply_text = "🎮 Похожие игры:\n\n"
        keyboard = []

        for game in similar:
            game_id = game.get('id')
            game_name = game.get('name')
            price = game.get('cheapest_price', 'Цена неизвестна')

            reply_text += f"• {game_name} - ${price}\n"
            keyboard.append([
                InlineKeyboardButton(f"Подробнее о {game_name}", callback_data=f"details_{game_id}")
            ])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(reply_text, reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Ошибка в similar_games: {e}")
        await update.message.reply_text("Извините, произошла ошибка при поиске похожих игр.")

async def price_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает историю цен игры."""
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите ID игры для просмотра истории цен. Пример: /history 12345")
        return

    game_id = context.args[0]
    await update.message.reply_text("Получаю историю цен...")

    try:
        history = await get_price_history(game_id)
        game_details = await get_game_details(game_id)

        if not history or not game_details:
            await update.message.reply_text("Не удалось получить историю цен.")
            return

        game_name = game_details.get('name', 'Неизвестная игра')
        reply_text = f"📊 История цен для {game_name}:\n\n"

        for i in range(len(history['dates'])):
            date = history['dates'][i]
            price = history['prices'][i]
            store = history['stores'][i]
            reply_text += f"📅 {date}\n💰 ${price} ({store})\n\n"

        await update.message.reply_text(reply_text)

    except Exception as e:
        logger.error(f"Ошибка в price_history: {e}")
        await update.message.reply_text("Извините, произошла ошибка при получении истории цен.")