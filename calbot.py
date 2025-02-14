import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler

# Состояния для диалога
SELECT_DATE, SELECT_START_TIME, SELECT_END_TIME, ADD_DESCRIPTION, DELETE_EVENT = range(5)

# Инициализация базы данных (в данном случае просто словарь)
events = {}  # {chat_id: [события]}

# Генерация клавиатуры для выбора даты
def generate_date_keyboard(back_button=False):
    keyboard = []
    today = datetime.now()
    
    # Список дней недели для перевода числового значения в название
    weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    
    for i in range(7):  # Показываем 7 дней от сегодняшнего
        date = today + timedelta(days=i)
        formatted_date = date.strftime("%d-%m")  # Форматируем дату как ДД-ММ
        weekday_name = weekdays[date.weekday()]  # Получаем название дня недели
        button_text = f"{formatted_date} ({weekday_name})"  # Добавляем день недели
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"date_{formatted_date}")])
    
    if back_button:
        keyboard.append([InlineKeyboardButton("Назад", callback_data="back")])
    
    return InlineKeyboardMarkup(keyboard)

# Генерация клавиатуры для выбора времени
def generate_time_keyboard(back_button=False):
    keyboard = []
    start_hour = 8  # Начинаем с 08:00
    end_hour = 18   # Заканчиваем на 18:00
    times = []

    for hour in range(start_hour, end_hour + 1):
        times.append(f"{hour:02d}:00")  # Полные часы (например, 08:00)
        if hour != end_hour:  # Добавляем полчаса, если не последний час
            times.append(f"{hour:02d}:30")  # Полчаса (например, 08:30)

    # Разбиваем временные слоты на строки по 3 кнопки
    for i in range(0, len(times), 3):
        row = [InlineKeyboardButton(times[j], callback_data=f"time_{times[j]}") for j in range(i, min(i + 3, len(times)))]
        keyboard.append(row)
    
    if back_button:
        keyboard.append([InlineKeyboardButton("Назад", callback_data="back")])
    
    return InlineKeyboardMarkup(keyboard)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_type = update.message.chat.type  # Тип чата: 'private', 'group', 'supergroup'
    
    if chat_type == "private":
        # Кнопки для личного чата
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("Добавить событие", callback_data="add_event")],
            [InlineKeyboardButton("Просмотреть события", callback_data="view_events")],
            [InlineKeyboardButton("Открыть мини-приложение", web_app=WebAppInfo(url="https://blazierxo.github.io"))]
        ])
        await update.message.reply_text(
            "Привет! Я ваш календарь-бот. Выберите действие:",
            reply_markup=reply_markup
        )
    else:
        # Сообщение для группы
        bot_username = context.bot.username
        await update.message.reply_text(
            f"Привет! Я работаю в группах, но некоторые функции доступны только в личных чатах. "
            f"Чтобы использовать мини-приложение, начните диалог со мной в личном чате: "
            f"[Нажмите здесь](https://t.me/{bot_username})",
            parse_mode="Markdown"
        )

# Обработчик inline-кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()  # Подтверждаем обработку запроса
    
    if query.data == "add_event":
        await query.edit_message_text(
            "Выберите дату события:",
            reply_markup=generate_date_keyboard(back_button=True)
        )
        return SELECT_DATE
    elif query.data.startswith("date_"):
        selected_date = query.data.split("_")[1]
        context.user_data["selected_date"] = selected_date
        await query.edit_message_text(
            "Выберите время начала события:",
            reply_markup=generate_time_keyboard(back_button=True)
        )
        return SELECT_START_TIME
    elif query.data.startswith("time_"):
        selected_time = query.data.split("_")[1]
        if "selected_start_time" not in context.user_data:
            # Сохраняем время начала
            context.user_data["selected_start_time"] = selected_time
            await query.edit_message_text(
                "Выберите время окончания события:",
                reply_markup=generate_time_keyboard(back_button=True)
            )
            return SELECT_END_TIME
        else:
            # Сохраняем время окончания
            context.user_data["selected_end_time"] = selected_time
            await query.edit_message_text("Введите описание события:")
            return ADD_DESCRIPTION
    elif query.data == "cancel":
        # Завершаем диалог и убираем клавиатуру
        await query.edit_message_text(
            "Диалог завершен. Для повторного вызова бота используйте команду /start."
        )
        return ConversationHandler.END
    elif query.data == "back":
        # Возвращаемся к предыдущему шагу
        if "selected_date" in context.user_data:
            del context.user_data["selected_date"]
            await query.edit_message_text(
                "Выберите дату события:",
                reply_markup=generate_date_keyboard(back_button=True)
            )
            return SELECT_DATE
        elif "selected_start_time" in context.user_data:
            del context.user_data["selected_start_time"]
            await query.edit_message_text(
                "Выберите время начала события:",
                reply_markup=generate_time_keyboard(back_button=True)
            )
            return SELECT_START_TIME
        else:
            await query.edit_message_text(
                "Привет! Я ваш календарь-бот. Выберите действие:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Добавить событие", callback_data="add_event")],
                    [InlineKeyboardButton("Просмотреть события", callback_data="view_events")],
                    [InlineKeyboardButton("Отмена", callback_data="cancel")]  # Кнопка "Отмена"
                ])
            )
            return ConversationHandler.END
    elif query.data == "view_events":
        chat_id = query.message.chat_id
        if chat_id not in events or not events[chat_id]:
            await query.edit_message_text(
                "У вас пока нет событий.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Добавить событие", callback_data="add_event")],
                    [InlineKeyboardButton("Назад", callback_data="back")]  # Кнопка "Назад"
                ])
            )
            return
        
        message = "Ваши события:\n"
        for i, event in enumerate(events[chat_id], 1):
            message += f"{i}. {event['date']} {event['start_time']}-{event['end_time']}: {event['description']}\n"
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Добавить событие", callback_data="add_event")],
                [InlineKeyboardButton("Назад", callback_data="back")]  # Кнопка "Назад"
            ])
        )

# Получение описания события
async def add_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    description = update.message.text.strip()
    chat_id = update.message.chat_id
    selected_date = context.user_data["selected_date"]
    selected_start_time = context.user_data["selected_start_time"]
    selected_end_time = context.user_data["selected_end_time"]
    
    if chat_id not in events:
        events[chat_id] = []
    
    current_year = datetime.now().strftime("%Y")
    event_date = f"{current_year}-{selected_date[3:5]}-{selected_date[0:2]}"  # Преобразуем ДД-ММ в ГГГГ-ММ-ДД
    
    events[chat_id].append({
        "date": event_date,
        "start_time": selected_start_time,
        "end_time": selected_end_time,
        "description": description,
        "notified_1_hour": False,
        "notified_15_min": False
    })
    await update.message.reply_text(
        f"Событие добавлено: {event_date} {selected_start_time}-{selected_end_time} - {description}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Добавить событие", callback_data="add_event")],
            [InlineKeyboardButton("Просмотреть события", callback_data="view_events")],
            [InlineKeyboardButton("Назад", callback_data="back")]  # Кнопка "Назад"
        ])
    )
    
    # Очищаем данные пользователя после добавления события
    context.user_data.clear()
    return ConversationHandler.END

# Удаление события
async def delete_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.message.chat_id
    try:
        event_index = int(update.message.text) - 1
        if event_index < 0 or event_index >= len(events[chat_id]):
            raise ValueError()
        
        removed_event = events[chat_id].pop(event_index)
        await update.message.reply_text(
            f"Событие удалено: {removed_event['date']} {removed_event['start_time']}-{removed_event['end_time']} - {removed_event['description']}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Добавить событие", callback_data="add_event")],
                [InlineKeyboardButton("Просмотреть события", callback_data="view_events")],
                [InlineKeyboardButton("Назад", callback_data="back")]  # Кнопка "Назад"
            ])
        )
    except (ValueError, IndexError):
        await update.message.reply_text(
            "Неверный номер события. Попробуйте снова.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Добавить событие", callback_data="add_event")],
                [InlineKeyboardButton("Просмотреть события", callback_data="view_events")],
                [InlineKeyboardButton("Назад", callback_data="back")]  # Кнопка "Назад"
            ])
        )
    
    return ConversationHandler.END

# Фоновая задача для проверки событий
async def check_events(context: ContextTypes.DEFAULT_TYPE) -> None:
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")
    
    for chat_id, chat_events in events.items():
        for event in chat_events[:]:  # Используем копию списка для безопасного удаления
            event_date = event["date"]
            start_time = event["start_time"]
            
            # Рассчитываем время уведомлений
            event_datetime = datetime.strptime(f"{event_date} {start_time}", "%Y-%m-%d %H:%M")
            notify_1_hour = event_datetime - timedelta(hours=1)
            notify_15_min = event_datetime - timedelta(minutes=15)
            
            # Текущее время
            now_datetime = datetime.now()
            
            # Уведомление за час
            if not event["notified_1_hour"] and notify_1_hour <= now_datetime < event_datetime:
                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"Напоминание: через час — {event['description']} ({event_date} {start_time}-{event['end_time']})"
                    )
                    event["notified_1_hour"] = True
                except Exception as e:
                    print(f"Не удалось отправить уведомление в чат {chat_id}: {e}")
            
            # Уведомление за 15 минут
            if not event["notified_15_min"] and notify_15_min <= now_datetime < event_datetime:
                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"Напоминание: через 15 минут — {event['description']} ({event_date} {start_time}-{event['end_time']})"
                    )
                    event["notified_15_min"] = True
                except Exception as e:
                    print(f"Не удалось отправить уведомление в чат {chat_id}: {e}")
            
            # Удаление события после его наступления
            if now_datetime >= event_datetime:
                try:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"Событие началось: {event['description']} ({event_date} {start_time}-{event['end_time']})"
                    )
                except Exception as e:
                    print(f"Не удалось отправить уведомление в чат {chat_id}: {e}")
                
                chat_events.remove(event)

# Обработчик сообщений от мини-приложения
async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Получаем данные из Web App
    data = update.message.web_app_data.data
    chat_id = update.message.chat_id

    # Парсим данные (ожидается JSON)
    try:
        event_data = json.loads(data)
        date = event_data.get("date")
        start_time = event_data.get("start_time")
        end_time = event_data.get("end_time")
        description = event_data.get("description")

        if not all([date, start_time, end_time, description]):
            await update.message.reply_text("Ошибка: неполные данные.")
            return

        # Сохраняем событие
        if chat_id not in events:
            events[chat_id] = []

        events[chat_id].append({
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            "description": description,
            "notified_1_hour": False,
            "notified_15_min": False
        })

        await update.message.reply_text(
            f"Событие добавлено: {date} {start_time}-{end_time} - {description}"
        )
    except json.JSONDecodeError:
        await update.message.reply_text("Ошибка: неверный формат данных.")

# Основная функция
def main() -> None:
    token = '7677523148:AAF5xf_NnYlu-h2HsJ9Hql9YOViV6THUjSc'  # Замените на ваш токен
    application = Application.builder().token(token).build()
    
    # Добавляем обработчики для команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(button_handler)
        ],
        states={
            SELECT_DATE: [CallbackQueryHandler(button_handler)],
            SELECT_START_TIME: [CallbackQueryHandler(button_handler)],
            SELECT_END_TIME: [CallbackQueryHandler(button_handler)],
            ADD_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_description)],
            DELETE_EVENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_event)],
        },
        fallbacks=[CallbackQueryHandler(button_handler, pattern="^cancel$|^back$")],
        per_chat=True,       # Отслеживать состояние для каждого чата
        per_user=False,      # Не отслеживать состояние для каждого пользователя
        per_message=False    # Не отслеживать состояние для каждого сообщения
    )
    
    application.add_handler(conv_handler)
    application.job_queue.run_repeating(check_events, interval=60, first=0)
    
    application.run_polling()

if __name__ == '__main__':
    main()