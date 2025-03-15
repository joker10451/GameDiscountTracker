import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.game_service import search_game, get_game_details
from services.price_tracker import get_current_discounts
from data.data_manager import add_subscription, remove_subscription, get_user_subscriptions, update_user_info
from flask import current_app

# Set up logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    user = update.effective_user
    
    # Save user info to database
    with current_app.app_context():
        try:
            update_user_info(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            logger.info(f"User data saved to database: {user.id}")
        except Exception as e:
            logger.error(f"Error saving user data: {e}")
    
    await update.message.reply_html(
        f"Привет, {user.mention_html()}! 👋\n\n"
        "Я бот отслеживания скидок на игры. Я помогу тебе отслеживать снижение цен на твои любимые игры "
        "в различных цифровых магазинах.\n\n"
        "Используй команду /help, чтобы увидеть список доступных команд."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_text = (
        "Вот команды, которые ты можешь использовать:\n\n"
        "/search <название_игры> - Поиск игры\n"
        "/subscribe <id_игры> - Подписаться на уведомления о цене\n"
        "/unsubscribe <id_игры> - Отписаться от уведомлений\n"
        "/mysubs - Показать список твоих подписок\n"
        "/discounts - Показать текущие скидки\n"
        "/filter price <макс_цена> - Установить фильтр по цене\n"
        "/filter discount <мин_скидка> - Установить фильтр по скидке\n"
        "/filter clear - Сбросить все фильтры\n"
        "/help - Показать это сообщение"
    )
    await update.message.reply_text(help_text)

async def search_games(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Search for games when the command /search is issued."""
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите название игры для поиска. Пример: /search Witcher 3")
        return
    
    query = ' '.join(context.args)
    await update.message.reply_text(f"Ищу: {query}...")
    
    try:
        results = await search_game(query)
        
        if not results:
            await update.message.reply_text(f"Не найдено игр по запросу '{query}'. Попробуйте другой поисковый запрос.")
            return
        
        # Create reply with inline buttons for each result
        reply_text = "🎮 Результаты поиска:\n\n"
        keyboard = []
        
        for idx, game in enumerate(results[:5]):  # Limit to 5 results to avoid message size limits
            game_id = game.get('id')
            game_name = game.get('name')
            
            reply_text += f"{idx+1}. {game_name} (ID: {game_id})\n"
            
            # Add button to subscribe and view details
            keyboard.append([
                InlineKeyboardButton(f"Подписаться на {game_name}", callback_data=f"sub_{game_id}"),
                InlineKeyboardButton(f"Подробности", callback_data=f"details_{game_id}")
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(reply_text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in search_games: {e}")
        await update.message.reply_text(f"Извините, произошла ошибка при поиске. Пожалуйста, попробуйте позже.")

async def subscribe_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Subscribe to price alerts for a game."""
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите ID игры, на которую хотите подписаться. Используйте /search для поиска ID игр.")
        return
    
    game_id = context.args[0]
    user_id = update.effective_user.id
    
    try:
        # Get game details first to verify it exists
        game_details = await get_game_details(game_id)
        
        if not game_details:
            await update.message.reply_text(f"Игра с ID {game_id} не найдена. Пожалуйста, проверьте ID и попробуйте снова.")
            return
        
        # Add subscription with app context
        with current_app.app_context():
            # Get thumbnail if available
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
        logger.error(f"Error in subscribe_game: {e}")
        await update.message.reply_text("Извините, произошла ошибка при подписке. Пожалуйста, попробуйте позже.")

async def unsubscribe_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Unsubscribe from price alerts for a game."""
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите ID игры, от которой хотите отписаться. Используйте /mysubs, чтобы увидеть ваши подписки.")
        return
    
    game_id = context.args[0]
    user_id = update.effective_user.id
    
    try:
        # Remove subscription with app context
        with current_app.app_context():
            success, game_name = remove_subscription(user_id, game_id)
        
            if success:
                await update.message.reply_text(f"✅ Вы отписались от уведомлений о цене для игры {game_name}.")
            else:
                await update.message.reply_text("Вы не подписаны на эту игру.")
            
    except Exception as e:
        logger.error(f"Error in unsubscribe_game: {e}")
        await update.message.reply_text("Извините, произошла ошибка при отписке. Пожалуйста, попробуйте позже.")

async def list_subscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all subscribed games for the user."""
    user_id = update.effective_user.id
    
    try:
        # Get subscriptions with app context
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
                
                # Add button to unsubscribe
                keyboard.append([
                    InlineKeyboardButton(f"Отписаться от {game_name}", callback_data=f"unsub_{game_id}")
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(reply_text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in list_subscriptions: {e}")
        await update.message.reply_text("Извините, произошла ошибка при получении ваших подписок. Пожалуйста, попробуйте позже.")

async def check_discounts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current game discounts."""
    await update.message.reply_text("Проверяю текущие скидки на игры... Это может занять некоторое время.")
    
    try:
        max_price = context.user_data.get('max_price')
        min_discount = context.user_data.get('min_discount')
        
        discounts = await get_current_discounts(
            max_price=max_price,
            min_discount=min_discount
        )
        
        if not discounts:
            await update.message.reply_text("В данный момент не найдено значительных скидок. Загляните позже!")
            return
        
        reply_text = "🔥 Текущие горячие предложения:\n\n"
        keyboard = []
        
        for game in discounts[:10]:  # Limit to 10 games to avoid message size limits
            game_id = game.get('id')
            game_name = game.get('name')
            discount = game.get('discount_percent', 0)
            current_price = game.get('price_current', 'Неизвестно')
            original_price = game.get('price_original', 'Неизвестно')
            store = game.get('store', 'Неизвестный магазин')
            
            reply_text += (f"🎮 {game_name}\n"
                         f"💰 {current_price} (было {original_price}, -{discount}%)\n"
                         f"🏪 {store}\n\n")
            
            # Add button to subscribe
            keyboard.append([
                InlineKeyboardButton(f"Подписаться на {game_name}", callback_data=f"sub_{game_id}"),
                InlineKeyboardButton(f"Подробности", callback_data=f"details_{game_id}")
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(reply_text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in check_discounts: {e}")
        await update.message.reply_text("Извините, произошла ошибка при получении текущих скидок. Пожалуйста, попробуйте позже.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button presses from inline keyboards."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    try:
        if data.startswith('sub_'):
            game_id = data[4:]
            user_id = update.effective_user.id
            
            # Get game details
            game_details = await get_game_details(game_id)
            
            if not game_details:
                await query.edit_message_text(text=f"Игра с ID {game_id} не найдена. Пожалуйста, попробуйте другую игру.")
                return
            
            # Add subscription with app context
            with current_app.app_context():
                # Get thumbnail if available
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
            
            # Remove subscription with app context
            with current_app.app_context():
                success, game_name = remove_subscription(user_id, game_id)
            
                if success:
                    await query.edit_message_text(text=f"✅ Вы отписались от уведомлений о цене для игры {game_name}.")
                else:
                    await query.edit_message_text(text="Вы не подписаны на эту игру.")
                
        elif data.startswith('details_'):
            game_id = data[8:]
            
            # Get game details
            game_details = await get_game_details(game_id)
            
            if not game_details:
                await query.edit_message_text(text=f"Игра с ID {game_id} не найдена. Пожалуйста, попробуйте другую игру.")
                return
            
            # Format game details message
            game_name = game_details.get('name', 'Неизвестная игра')
            stores = game_details.get('stores', [])
            prices = game_details.get('prices', {})
            
            details_text = f"🎮 {game_name}\n\n"
            
            if 'description' in game_details:
                # Truncate description if it's too long
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
            
            # Add button to subscribe
            keyboard = [[InlineKeyboardButton(f"Подписаться на {game_name}", callback_data=f"sub_{game_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text=details_text, reply_markup=reply_markup)
            
    except Exception as e:
        logger.error(f"Error in button_handler: {e}")
        await query.edit_message_text(text="Извините, произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by updates."""
    logger.error(f"Update {update} caused error {context.error}")
    
    # Notify user of error
    if update.effective_message:
        await update.effective_message.reply_text("Извините, что-то пошло не так. Пожалуйста, попробуйте позже.")


async def handle_filters(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle price and discount filters"""
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
