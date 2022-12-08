from django.core.management.base import BaseCommand
from mail_bot import settings
from telebot import TeleBot, types
from samples.management.commands.email_handlers.email_funcs import get_mail_server, get_unseen_mails
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

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Добавить новую почту")
    btn2 = types.KeyboardButton("TODO")
    markup.add(btn1, btn2)
    # TODO добавить нормальное стартовое сообщение
    bot.send_message(
        message.chat.id,
        f"Привет, {message.from_user.first_name}",
        reply_markup=markup
    )


@log_errors
@bot.message_handler(content_types=['text'])
def get_message(message):
    if message.text == "Добавить новую почту":
        select_mail_login(message)


def select_mail_login(message):
    bot.send_message(message.chat.id, f"Введите логин:")
    bot.register_next_step_handler(message, get_mail_login)


def get_mail_login(message):
    bot.send_message(message.chat.id, f"Введите пароль:")
    bot.register_next_step_handler(message, save_mail, message.text)


def save_mail(message, mail_login):
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
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton("Добавить новую почту")
        btn2 = types.KeyboardButton("Мои добавленные почты")
        markup.add(btn1, btn2)
        bot.send_message(message.chat.id, f"Почта успешно добавлена", reply_markup=markup)


class Command(BaseCommand):
    help = 'MailBot'

    def handle(self, *args, **options):
        bot.enable_save_next_step_handlers(delay=2)
        bot.load_next_step_handlers()
        bot.infinity_polling()
