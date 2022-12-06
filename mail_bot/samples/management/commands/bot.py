from django.core.management.base import BaseCommand
from mail_bot import settings
from telebot import TeleBot, types

from samples.models import User, Mailbox

bot = TeleBot(token=settings.TELEGRAM_TOKEN)

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
    #TODO добавить нормальное стартовое сообщение
    bot.send_message(
        message.chat.id,
        f"Привет, {message.from_user.first_name}",
        reply_markup=markup
    )

@log_errors
@bot.message_handler(content_types=['text'])
def get_message(message):
    if message.text == "Добавить новую почту":
        select_mail_id(message)


def select_mail_id(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn1 = types.KeyboardButton("Yandex")
    btn2 = types.KeyboardButton("Gmail")
    markup.add(btn1, btn2)
    bot.send_message(
        message.chat.id,
        f"Выберите почту, в которой хотите авторизоваться",
        reply_markup=markup
    )
    bot.register_next_step_handler(message, get_mail_id)


def get_mail_id(message):
    bot.send_message(message.chat.id, f"Введите почту:")
    bot.register_next_step_handler(message, get_mail_login, message.text)


def get_mail_login(message, mail_id):
    bot.send_message(message.chat.id, f"Введите пароль от почты:")
    bot.register_next_step_handler(message, get_mail_password_and_put_in_db, mail_id, message.text)


def get_mail_password_and_put_in_db(message, mail_id, mail_login):
    mb, _ = Mailbox.objects.get_or_create(
      defaults={
          'mail_id': mail_id,
          'login': mail_login,
          'password': message.text,
          'user': User.objects.get(telegram_id=message.from_user.username)
      }
    )

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Добавить")
    btn2 = types.KeyboardButton("функции")
    markup.add(btn1, btn2)
    bot.send_message(message.chat.id, f"Почта успешно добавлена!", reply_markup=markup)

class Command(BaseCommand):
    help = 'MailBot'

    def handle(self, *args, **options):
        bot.enable_save_next_step_handlers(delay=2)
        bot.load_next_step_handlers()
        bot.infinity_polling()
