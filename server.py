import logging
from telegram.ext import CommandHandler, Application, MessageHandler, filters
from telegram import ReplyKeyboardMarkup
from telegram.ext import ConversationHandler
import sqlite3
from config import BOT_TOKEN

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

reply_keyboard = [['/help']]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=False)

tasks = {}  # Словарь для хранения задач
count_completed_tasks = 0  # Количество выполенных задач

# Определение различных состояний
ENTER_TITLE, ENTER_DESCRIPTION = range(2)  # добавление задач
ENTER_TASK = range(1)  # вывод задачи по названию
ENTER_TASK2, ENTER_RESPONSIBLE_PERSON, ENTER_DEADLINE = range(3)  # добавление ответсвенного и срока выполнения
ENTER_USER = range(1)  # вывод всех задач пользователя
ENTER_TASK3 = range(1)  # выполнение задачи
ENTER_TASK4 = range(1)  # удаление задачи
ENTER_TASK5, NAME_EDIT, ENTER_NEW_NAME = range(3)  # изменение задачи


async def start(update, context):
    user = update.effective_user
    await update.message.reply_html(
        f"Добро пожаловать в бот-планировщик, {user.mention_html()}!\n"
        "Создайте профиль при помощи команды /add_user!\n"
        "Чтобы просмотреть все возможности бота, воспользуйтесь командой /help.",
        reply_markup=markup,
        reply=ReplyKeyboardMarkup([["/cancel"]], resize_keyboard=True, one_time_keyboard=False)

    )
    return ConversationHandler.END


# Подсказки с возможными командами бота
async def help(update, context):
    await update.message.reply_text(
        '/add_task - добавление задачи\n'
        '/assign_task - добавление ответственного за задачу и срок её выполнения.\n'
        '/list_task - список всех задач, вместе с ее ответственными и сроком выполнения.\n'
        '/get_task - информация о конкретной задаче\n'
        '/delete_task - удаление задачи\n'
        '/complete_task - выполнение задачи.\n'
        '/responsible_task - вывод всех пользователей.\n'
        '/edit_task - редактирование задач.\n'
        '/user_task вывод задач по пользователю.\n'
        '/add_user - заполнить информацию о себе (используеться когда профиль пуст) в профиль.\n'
        '/add_info - добавить (дополнить) информацию о себе в профиль.\n'
        '/profile - посмотреть информацию о себе в профиле.\n'
        '/delete_info - удалить информацию о себе из профиля.\n\n'
        'Если Вы нажали на какую-то команду и хотите её отменить, то воспользуйтесь /cancel'
    )
    return ConversationHandler.END


# добавление первой информации о пользователе, переход в состояние добавления
async def add_user(update, context):
    await update.message.reply_text(
        f"Введите информацию о себе, которая будет отображаться в Вашем профиле",
    )
    return "WAITING_FOR_NAME"


# измемение информации переход в состояние обновления
async def add_info(update, context):
    await update.message.reply_text(
        f"Введите информацию о себе, которую хотите добавить в профиль",
    )
    return "WAITING_FOR_UPDATE_INFO"


# сохранение первой информации о пользоваетеле
async def handle_user_info(update, context):
    user_info = update.message.text
    chat_id = update.effective_chat.id

    # Соединение с базой данных
    conn = sqlite3.connect('user.db')
    cursor = conn.cursor()

    # Создание таблицы, если она еще не существует
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            user_info TEXT
        )
    ''')

    # Сохранение данных в базу данных
    cursor.execute('''
        INSERT INTO users (chat_id, user_info) VALUES (?, ?)
    ''', (chat_id, user_info))

    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"Информация '{user_info}' успешно сохранена."
    )
    return ConversationHandler.END


# профиль где записана информация о пользователе.
async def profile(update, context):
    # Получаем информацию о пользователе из базы данных
    conn = sqlite3.connect('user.db')
    cursor = conn.cursor()
    user_id = update.effective_user.id
    cursor.execute("SELECT * FROM users WHERE chat_id = ?", (user_id,))
    user_info = cursor.fetchone()

    # Если пользователь не найден в базе данных, отправляем сообщение об ошибке
    if user_info is None:
        await update.message.reply_text("Вы еще не добавили информацию о себе. Используйте команду /add_user.")
    else:
        # Формируем сообщение с информацией о пользователе
        message = f"Ваша информация:\n{user_info[1]}"
        await update.message.reply_text(message)

    conn.close()
    return ConversationHandler.END


# обновление информации
async def update_info(update, context):
    user_info = update.message.text
    chat_id = update.effective_chat.id

    # Соединение с базой данных
    conn = sqlite3.connect('user.db')
    cursor = conn.cursor()

    # Получаем текущую информацию о пользователе
    cursor.execute("SELECT user_info FROM users WHERE chat_id = ?", (chat_id,))
    current_info = cursor.fetchone()

    # Если пользователь уже добавил информацию
    if current_info is not None:
        # Объединяем текущую информацию и новую информацию в одну строку
        combined_info = f"{current_info[0]}\n{user_info}"
    else:
        combined_info = user_info

    # Обновление данных в базе данных
    cursor.execute('''
        UPDATE users SET user_info = ? WHERE chat_id = ?
    ''', (combined_info, chat_id))

    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"Информация '{user_info}' успешно обновлена."
    )
    return ConversationHandler.END


# Функции для удаления информации о пользователе
# подтверждение удаления информации из профиля
async def delete_info(update, context):
    await update.message.reply_text(f'Вы точно хотите удалить информацию из профиля?',
                                    reply_markup=ReplyKeyboardMarkup(
                                        [["Да"], ["Нет"]],
                                        resize_keyboard=True, one_time_keyboard=False))
    return "DELE"


# удаление информации из профиля
async def delete_info_user(update, context):
    subject = update.message.text
    user_id = update.effective_user.id

    # Соединение с базой данных
    conn = sqlite3.connect('user.db')
    cursor = conn.cursor()
    if subject == 'Да':
        # Удаление данных о пользователе из базы данных
        cursor.execute('''
            DELETE FROM users WHERE chat_id = ?
        ''', (user_id,))
        await update.message.reply_text(
            f"Информация о Вас успешно удалена из профиля.",
            reply_markup=markup,
            reply=ReplyKeyboardMarkup([["/cancel"]], resize_keyboard=True, one_time_keyboard=False)

        )
    if subject == 'Нет':
        await update.message.reply_text(
            f"Действие отменено.",
            reply_markup=markup,
            reply=ReplyKeyboardMarkup([["/cancel"]], resize_keyboard=True, one_time_keyboard=False)
        )
    conn.commit()
    conn.close()
    return ConversationHandler.END


# Ответ на неизвестное сообщение
async def unknown(update, context):
    await update.message.reply_text(
        "Извините, я не могу понять Ваш запрос. Пожалуйста, воспользуйтесь командой /help для получения помощи.")


# Добавление задачи
async def add_task(update, context):
    await update.message.reply_text("Введите название задачи, которую хотите добавить в список задач")
    return ENTER_TITLE


# Ввод названия задачи
async def enter_title(update, context):
    context.user_data['title'] = update.message.text
    await update.message.reply_text("Введите описание задачи")
    return ENTER_DESCRIPTION


# Ввод описания задачи
async def enter_description(update, context):
    context.user_data['description'] = update.message.text
    title = context.user_data['title']
    description = context.user_data['description']
    tasks[title] = []
    tasks[title].append(description)
    tasks[title].append('не указан')
    tasks[title].append('не указан')

    # Добавление задачи в Вашу систему
    await update.message.reply_text(
        f"Задача <b>{title}</b> с описанием <b>{description}</b> успешно добавлена!\n"
        f"Чтобы назначить ответственного и срок выполнения, воспользуйтесь командой /assign_task", parse_mode='html')
    return ConversationHandler.END


# Отмена операции
async def cancel(update, context):
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END


# Вывод всех задач
async def list_task(update, context):
    if len(tasks) == 0:
        await update.message.reply_text(
            "У вас нет задач.\n"
            "Чтобы добавить задачи, воспользуйтесь функцией /add_task"
        )
        return ConversationHandler.END
    else:
        task_list = "\n".join(
            [f"{key}: {value[0]}, исполнитель - {value[1]}, срок выполнения - {value[2]}" for key, value in
             tasks.items()])
        await update.message.reply_text(f"Список задач:\n{task_list}\n")
        return ConversationHandler.END


# Вывод задачи по названию
async def get_task(update, context):
    await update.message.reply_text("Введите название задачи, информацию о которой хотите увидеть")
    return ENTER_TASK


# Ввод названия задачи
async def enter_task(update, context):
    title = update.message.text
    if title in tasks:
        await update.message.reply_text(
            f'Задача <b>{title}</b>:\n'
            f'Описание - <b>{tasks[title][0]}</b>, исполнитель - <b>{tasks[title][1]}</b>, '
            f'срок выполнения - <b>{tasks[title][2]}</b>', parse_mode='html')
    else:
        await update.message.reply_text(
            f'Задача с названием <b>{title}</b> не найдена.\n'
            f'Можете просмотреть список своих задач при помощи команды /list_task или воспользуйтесь командой /help',
            parse_mode='html')
    return ConversationHandler.END


# Добавление отвественного за исполнение задачи; дедлайн
async def assign_task(update, context):
    await update.message.reply_text(
        "Ведите название задачи, для которой хотите назначить отвественного и срок выполнения")
    return ENTER_TASK2


# Ввод названия задачи
async def enter_task2(update, context):
    context.user_data['title'] = update.message.text
    title = context.user_data['title']
    if title not in tasks:
        await update.message.reply_text(f'Задача с названием <b>{title}</b> не найдена.\n'
                                        f'Можете просмотреть список своих задач при помощи команды /list_task',
                                        parse_mode='html')
        return ConversationHandler.END
    await update.message.reply_text(f'Введите ответственного для выполнения задачи <b>{title}</b>', parse_mode='html')
    return ENTER_RESPONSIBLE_PERSON


# Ввод ответственного
async def enter_responsible_person(update, context):
    context.user_data['person'] = update.message.text
    title = context.user_data['title']
    person = context.user_data['person']
    tasks[title][1] = person
    await update.message.reply_text(f'Введите срок выполнения')
    return ENTER_DEADLINE


# Ввод срока выполнения
async def enter_deadline(update, context):
    deadline = update.message.text
    title = context.user_data['title']
    person = context.user_data['person']
    tasks[title][2] = deadline
    await update.message.reply_text(f'Ответственный - <b>{person}</b> для задания <b>{title}</b> назначен.\n'
                                    f'Срок выполнения <b>{deadline}</b> установлен.', parse_mode='html')
    return ConversationHandler.END


# Список задач пользователя
async def user_task(update, context):
    await update.message.reply_text('Введите имя пользователя, список задач которого хотите просмотреть')
    return ENTER_USER


# Ввод имени пользователя
async def enter_user(update, context):
    user = update.message.text
    tasks_user = []
    for task in tasks:
        if user in tasks[task]:
            tasks_user.append(task)
    if len(tasks_user) > 0:
        tasks_list = "\n".join(
            [f"{task}: {tasks[task][0]}, исполнитель - {tasks[task][1]}, срок выполнения - {tasks[task][2]}" for
             task in tasks_user])
        await update.message.reply_text(
            f'Задачи пользователя <b>{user}</b>:\n{tasks_list}', parse_mode='html')
        return ConversationHandler.END
    else:
        await update.message.reply_text(f'Задачи пользователя <b>{user}</b> не найдены.', parse_mode='html')
        return ConversationHandler.END


# Вывод всех пользователей, ответственных за задачи
async def responsible_task(update, context):
    responsible_users = set()
    for task, details in tasks.items():
        responsible_user = details[1]
        responsible_users.add(responsible_user)

    if responsible_users:
        response_message = "Пользователи, ответственные за задачи:\n"
        for user in responsible_users:
            response_message += f"{user}\n"
        await update.message.reply_text(response_message)
    else:
        await update.message.reply_text("Пока нет пользователей, ответственных за задачи.")
    return ConversationHandler.END


# Выполнение задачи
async def complete_task(update, context):
    await update.message.reply_text("Ведите название задачи, которую хотите завершить")
    return ENTER_TASK3


# Ввод названия задачи
async def enter_task3(update, context):
    global count_completed_tasks

    task = update.message.text
    if task in tasks:
        del tasks[task]
        count_completed_tasks += 1
        await update.message.reply_text(
            f'Задача <b>{task}</b> выполнена. Поздравляем!\n'
            f'Вы выполнили {count_completed_tasks} задач!', parse_mode='html')
    else:
        await update.message.reply_text(f'Задача с названием <b>{task}</b> не найдена.', parse_mode='html')
    return ConversationHandler.END


# Удаление задачи
async def delete_task(update, context):
    await update.message.reply_text("Ведите название задачи, которую хотите удалить из списка Ваших задач")
    return ENTER_TASK4


# Ввод названия задачи
async def enter_task4(update, context):
    task = update.message.text
    if task in tasks:
        del tasks[task]
        await update.message.reply_text(f'Задача <b>{task}</b> успешно удалена.', parse_mode='html')
    else:
        await update.message.reply_text(f'Задача с названием <b>{task}</b> не найдена.', parse_mode='html')
    return ConversationHandler.END


# Изменение (названия, описания, ответственного, срока выполенния)
async def edit_task(update, context):
    await update.message.reply_text("Введите название задачи, которую хотите редактировать")
    return ENTER_TASK5


# Ввод названия задачи
async def enter_task5(update, context):
    context.user_data['task'] = update.message.text
    task = context.user_data['task']
    if task not in tasks:
        await update.message.reply_text(f'Задача с названием <b>{task}</b> не найдена.', parse_mode='html')
        return ConversationHandler.END
    subject = update.message.text  # Используем содержимое сообщения, отправленного при нажатии на кнопку
    context.user_data['subject'] = subject
    await update.message.reply_text(f'Что Вы хотите редактировать?',
                                    reply_markup=ReplyKeyboardMarkup(
                                        [["Название"], ["Описание"], ["Ответственный"], ["Срок выполнения"]],
                                        resize_keyboard=True, one_time_keyboard=False))
    return NAME_EDIT


# Ввод того, что именно нужно изменить (название/описание/ответственного/срок выполенния)
async def name_edit(update, context):
    subject = update.message.text
    subject = subject.lower()
    context.user_data['subject'] = subject
    if subject not in ['название', 'описание', 'ответственный', 'срок выполнения']:
        await update.message.reply_text('Извините, я не могу понять Ваш запрос.\n'
                                        'Изменить можно: Название/Описание/Ответственный/Срок выполнения')
        return ConversationHandler.END
    if subject == 'название' or subject == 'описание':
        await update.message.reply_text(f'Введите новое {subject}',
                                        reply_markup=markup)
    elif subject == 'ответственный':
        await update.message.reply_text(f'Введите нового ответственного',
                                        reply_markup=markup)
    elif subject == 'срок выполнения':
        await update.message.reply_text(f'Введите новый срок выполнения',
                                        reply_markup=markup)
    return ENTER_NEW_NAME


# Ввод нового значения
async def enter_new_name(update, context):
    new_name = update.message.text
    task = context.user_data['task']
    subject = context.user_data['subject']

    if subject == 'название':
        tasks[new_name] = tasks[task]
        del tasks[task]
        await update.message.reply_text('Новое название установлено.')
    elif subject == 'описание':
        tasks[task][0] = new_name
        await update.message.reply_text('Новое описание установлено.')
    elif subject == 'ответственный':
        tasks[task][1] = new_name
        await update.message.reply_text('Новый ответственный установлен.')
    elif subject == 'срок выполнения':
        tasks[task][2] = new_name
        await update.message.reply_text('Новый срок выполнения установлен.')
    return ConversationHandler.END


def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))

    application.add_handler(CommandHandler("profile", profile))
    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('add_user', add_user), CommandHandler('add_info', add_info)],
        states={"WAITING_FOR_NAME": [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_info)],
                "WAITING_FOR_UPDATE_INFO": [MessageHandler(filters.TEXT & ~filters.COMMAND, update_info)]},
        fallbacks=[MessageHandler(filters.COMMAND, unknown)],
    )
    application.add_handler(conversation_handler)

    del_user_info = ConversationHandler(
        entry_points=[CommandHandler('delete_info', delete_info)],
        states={"DELE": [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_info_user)]},
        fallbacks=[MessageHandler(filters.COMMAND, unknown)],
    )
    application.add_handler(del_user_info)

    adding_tasks = ConversationHandler(
        entry_points=[CommandHandler('add_task', add_task)],
        states={
            ENTER_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_title)],
            ENTER_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_description)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    application.add_handler(adding_tasks)

    application.add_handler(CommandHandler("list_task", list_task))

    getting_task = ConversationHandler(
        entry_points=[CommandHandler('get_task', get_task)],
        states={
            ENTER_TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_task)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    application.add_handler(getting_task)

    assigning_task = ConversationHandler(
        entry_points=[CommandHandler('assign_task', assign_task)],
        states={
            ENTER_TASK2: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_task2)],
            ENTER_RESPONSIBLE_PERSON: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_responsible_person)],
            ENTER_DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_deadline)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    application.add_handler(assigning_task)

    person_task = ConversationHandler(
        entry_points=[CommandHandler('user_task', user_task)],
        states={
            ENTER_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_user)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    application.add_handler(person_task)

    application.add_handler(CommandHandler("responsible_task", responsible_task))

    completing_task = ConversationHandler(
        entry_points=[CommandHandler('complete_task', complete_task)],
        states={
            ENTER_TASK3: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_task3)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    application.add_handler(completing_task)

    deleting_task = ConversationHandler(
        entry_points=[CommandHandler('delete_task', delete_task)],
        states={
            ENTER_TASK4: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_task4)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    application.add_handler(deleting_task)

    editing_task = ConversationHandler(
        entry_points=[CommandHandler('edit_task', edit_task)],
        states={
            ENTER_TASK5: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_task5)],
            NAME_EDIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, name_edit)],
            ENTER_NEW_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_new_name)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    application.add_handler(editing_task)

    application.add_handler(MessageHandler(filters.COMMAND, unknown))  # ввод непонятного текстового сообщения
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))  # ввод неправильной команды
    application.run_polling()


if __name__ == '__main__':
    main()