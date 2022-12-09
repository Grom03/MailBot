from django.core.management.base import BaseCommand
from mail_bot import settings
from telebot import TeleBot, types
from samples.management.commands.email_handlers.email_funcs import get_mail_server, get_unseen_mails, get_emails_by_filter, create_filter
import logging

from samples.models import User, Mailbox

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

bot = TeleBot(token=settings.TELEGRAM_TOKEN)

EMAILS = {
    "Yandex": {
        "host": "imap.yandex.ru",
        "port": 993
    },
    "Google": {
        "host": "imap.gmail.com",
        "port": 993
    }
}

CANCEL_STR = "Отменить"
ADD_NEW_MAIL_STR = "Добавить новую почту"
GET_MESSAGES_STR = "Посмотреть недавние сообщения"
GET_ALL_NEW_STR = "Показать все новые"
SET_SENDER_STR = "Указать отправителя"
SET_DATE_FROM = "Настроить дату начала"
FILTERS_DONE = "Готово"

def get_cancel_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton(CANCEL_STR)
    markup.add(btn1)
    return markup

def get_default_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton(ADD_NEW_MAIL_STR)
    btn2 = types.KeyboardButton("Мои добавленные почты")
    btn3 = types.KeyboardButton(GET_MESSAGES_STR)
    markup.add(btn1, btn2, btn3)
    return markup

def get_default_filters_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton(GET_ALL_NEW_STR)
    btn2 = types.KeyboardButton(SET_SENDER_STR)
    btn3 = types.KeyboardButton(SET_DATE_FROM)
    markup.add(btn1, btn2, btn3)
    return markup

def get_edit_filters_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton(SET_SENDER_STR)
    btn2 = types.KeyboardButton(SET_DATE_FROM)
    btn3 = types.KeyboardButton(FILTERS_DONE)
    markup.add(btn1, btn2, btn3)
    return markup

def log_errors(func):
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as error:
            error_message = f'Произошла ошибка: {error}'
            print(error_message)
            raise error

    return inner


@log_errors
@bot.message_handler(commands=['start'])
def start_message(message):
    p, _ = User.objects.get_or_create(
        defaults={
            'telegram_id': message.from_user.username
        }
    )

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton(ADD_NEW_MAIL_STR)
    markup.add(btn1)
    # TODO добавить нормальное стартовое сообщение
    bot.send_message(
        message.chat.id,
        f"Привет, {message.from_user.first_name}",
        reply_markup=markup
    )


@log_errors
@bot.message_handler(content_types=['text'])
def get_message(message):
    if message.text == ADD_NEW_MAIL_STR:
        select_mail_login(message)
    if message.text == CANCEL_STR:
        bot.send_message(message.chat.id, "Отмена", reply_markup=get_default_markup())
    if message.text == GET_MESSAGES_STR:
        select_mailbox(message)

def select_mailbox(message):
    if message.text == CANCEL_STR:
        bot.send_message(message.chat.id, "Отмена", reply_markup=get_default_markup())
        return
    user = User.objects.get(telegram_id=message.from_user.username)
    mailboxes = user.mailboxes.all()
    text = "Укажите адрес почты (число)\n"
    for i, mailbox in enumerate(mailboxes):
        text += str(i + 1) + ". " + mailbox.login + "\n"
    bot.send_message(message.chat.id, text, reply_markup=get_cancel_markup())
    bot.register_next_step_handler(message, read_selected_mailbox)

def read_selected_mailbox(message):
    if message.text == CANCEL_STR:
        bot.send_message(message.chat.id, "Отмена", reply_markup=get_default_markup())
        return
    user = User.objects.get(telegram_id=message.from_user.username)
    mailboxes = user.mailboxes.all()
    try:
        count = int(message.text) - 1
        mb = mailboxes[count]
        bot.send_message(message.chat.id, "Настроить фильтры?", reply_markup=get_default_filters_markup())
        current_filter = 'UNSEEN'
        bot.register_next_step_handler(message, filter_enricher, current_filter, mb)
    except:
        bot.send_message(message.chat.id, "Ошибка, попробуйте позже", reply_markup=get_default_markup())
    

def filter_enricher(message, current_filter, mb):
    if message.text == CANCEL_STR:
        bot.send_message(message.chat.id, "Отмена", reply_markup=get_default_markup())
        return
    if message.text == GET_ALL_NEW_STR or message.text == FILTERS_DONE:
        show_messages(message, current_filter, mb)
    if message.text == SET_SENDER_STR:
        bot.send_message(message.chat.id, "Укажите желаемого отправителя", reply_markup=get_cancel_markup())
        new_filter_type = "FROM"
        bot.register_next_step_handler(message, filter_enricher_ack, current_filter, new_filter_type, mb)
    if message.text == SET_DATE_FROM:
        bot.send_message(message.chat.id, "Укажите желаемую дату начала в формате 19-Sep-2022", reply_markup=get_cancel_markup())
        new_filter_type = "SENTSINCE"
        bot.register_next_step_handler(message, filter_enricher_ack, current_filter, new_filter_type, mb)

def filter_enricher_ack(message, current_filter, new_filter_type, mb):
    if message.text == CANCEL_STR:
        bot.send_message(message.chat.id, "Отмена", reply_markup=get_edit_filters_markup())
        return
    current_filter += f' {new_filter_type} {message.text}'
    bot.send_message(message.chat.id, "Фильтр добавлен", reply_markup=get_edit_filters_markup())
    bot.register_next_step_handler(message, filter_enricher, current_filter, mb)


def show_messages(message, filter, mb: Mailbox):
    print("showing emails ", mb.login, mb.password)
    # TODO custom HOST and PORT
    mail_server = get_mail_server(mb.login, mb.password, EMAILS["Yandex"]["host"], EMAILS["Yandex"]["port"])
    # TODO custom mails number
    get_emails_by_filter(mail_server, filter, 1)
    text = get_emails_by_filter[0]
    bot.send_message(message.chat.id, text, reply_markup=get_default_markup())

def select_mail_login(message):
    if message.text == CANCEL_STR:
        bot.send_message(message.chat.id, "Отмена", reply_markup=get_default_markup())
        return
    bot.send_message(message.chat.id, f"Введите логин:", reply_markup=get_cancel_markup())
    bot.register_next_step_handler(message, get_mail_login)


def get_mail_login(message):
    if message.text == CANCEL_STR:
        bot.send_message(message.chat.id, "Почта не добавлена", reply_markup=get_default_markup())
        return
    bot.send_message(message.chat.id, f"Введите пароль:", reply_markup=get_cancel_markup())
    bot.register_next_step_handler(message, save_mail, message.text)


def save_mail(message, mail_login):
    if message.text == CANCEL_STR:
        bot.send_message(message.chat.id, "Почта не добавлена", reply_markup=get_default_markup())
        return
    mail_password = message.text
    mail_id = ""
    logging.info(f"Login and password {mail_login}, {mail_password}")
    check_yandex_mail = get_mail_server(mail_login, mail_password, EMAILS["Yandex"]["host"], EMAILS["Yandex"]["port"])
    check_google_mail = get_mail_server(mail_login, mail_password, EMAILS["Google"]["host"], EMAILS["Google"]["port"])
    if check_yandex_mail:
        mail_id = "Yandex"
    elif check_google_mail:
        mail_id = "Google"
    else:
        bot.send_message(message.chat.id, f"Неправильный логин или пароль")
    if mail_id != "":
        mb, _ = Mailbox.objects.get_or_create(
            defaults={
                'mail_id': mail_id,
                'login': mail_login,
                'password': mail_password,
                'user': User.objects.get(telegram_id=message.from_user.username)
            }
        )
        markup = get_default_markup()
        bot.send_message(message.chat.id, f"Почта успешно добавлена", reply_markup=markup)


class Command(BaseCommand):
    help = 'MailBot'

    def handle(self, *args, **options):
        bot.enable_save_next_step_handlers(delay=2)
        bot.load_next_step_handlers()
        bot.infinity_polling()
