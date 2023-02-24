import logging
import time

from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from samples.management.commands.email_handlers.email_funcs import get_mail_server, get_emails_by_filter
from samples.models import User, Mailbox
from telebot import TeleBot, types

from mail_bot import settings

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
ADD_MAIL_STR = "Добавить почту"
GET_MESSAGES_STR = "Посмотреть недавние сообщения"
CHANGE_MAILBOX = "Поменять почту"
GET_CURRENT_FILTER = "Оставить текущий фильтр"
CREATE_NEW_FILTER = "Настроить новый фильтр"
GET_ALL_NEW_STR = "Показать все новые"
SET_SENDER_STR = "Указать отправителя"
SET_DATE_FROM = "Настроить дату начала"
FILTERS_DONE = "Готово"
OAUTH_AUTHORIZATION = "OAuth Token"
PASSWORD_AUTHORIZATION = "Password"

FILTER_TYPE = {
    "Все письма": "ALL",
    "Непрочитанные": "UNSEEN",
    "Неотвеченные": "UNANSWERED"
}


def change_is_active(user, mb, is_active):
    mail_box = Mailbox.objects.get(
        user=user,
        login=mb.login
    )
    mail_box.is_active_search = is_active
    mail_box.save()


def get_is_active(user, mb):
    mail_box = Mailbox.objects.get(
        user=user,
        login=mb.login
    )
    return mail_box.is_active_search


def update_filter_in_db(user, mb, filter, filter_translation):
    mail_box = Mailbox.objects.get(
        user=user,
        login=mb.login
    )
    mail_box.filter = filter
    mail_box.filter_translation = filter_translation
    mail_box.save()


def mail_type_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("Все письма")
    btn2 = types.KeyboardButton("Непрочитанные")
    btn3 = types.KeyboardButton("Неотвеченные")
    markup.add(btn1, btn2, btn3)
    return markup


def get_cancel_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton(CANCEL_STR)
    markup.add(btn1)
    return markup

def get_default_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton(CHANGE_MAILBOX)
    btn2 = types.KeyboardButton(GET_MESSAGES_STR)
    markup.add(btn1, btn2)
    return markup


def get_auth_types():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton(OAUTH_AUTHORIZATION)
    btn2 = types.KeyboardButton(PASSWORD_AUTHORIZATION)
    markup.add(btn1, btn2)
    return markup

def get_current_filter_or_create_new():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton(GET_CURRENT_FILTER)
    btn2 = types.KeyboardButton(CREATE_NEW_FILTER)
    markup.add(btn1, btn2)
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
    p, created = User.objects.get_or_create(
        defaults={
            'telegram_id': message.from_user.username
        }
    )
    if created:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        btn1 = types.KeyboardButton(ADD_MAIL_STR)
        markup.add(btn1)
        bot.send_message(
            message.chat.id,
            f"Привет, {message.from_user.first_name}!\nДля начала работы с MailBot предлагаем создать пустой почтовый ящик,"
            f"чтобы использовать его как сборщик почты с твоих личных почтовых ящиков. После создания нового аккаунта, "
            f"просто добавь данные о почтовом ящике, нажав кнопку \"Добавить почту\". Далее рекомендуем настроить фильтры и "
            f"ждать нужного письма!",
            reply_markup=markup
        )
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        btn1 = types.KeyboardButton(CHANGE_MAILBOX)
        btn2 = types.KeyboardButton(GET_MESSAGES_STR)
        markup.add(btn1, btn2)
        bot.send_message(message.chat.id,
                         f"Привет, {message.from_user.first_name}!\nАдрес твоей почты - {p.mailbox.login}")


@log_errors
@bot.message_handler(content_types=['text'])
def get_message(message):
    if message.text == ADD_MAIL_STR:
        select_mail_login(message)
    if message.text == CANCEL_STR:
        bot.send_message(message.chat.id, "Отмена", reply_markup=get_default_markup())
    if message.text == GET_MESSAGES_STR:
        select_mailbox(message)
    if message.text == CHANGE_MAILBOX:
        select_mail_login(message)


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
        text = "Ваш текущий фильтр: " + mb.filter_translation + "\n\n\nНастроить новый фильтр или использовать текущий?"
        bot.send_message(message.chat.id, text, reply_markup=get_current_filter_or_create_new())
        bot.register_next_step_handler(message, new_filter_or_default, mb)
    except:
        bot.send_message(message.chat.id, "Ошибка, попробуйте позже", reply_markup=get_default_markup())


def new_filter_or_default(message, mb):
    if message.text == GET_CURRENT_FILTER:
        change_is_active(
            user=User.objects.get(telegram_id=message.from_user.username),
            mb=mb,
            is_active=True
        )
        show_messages(message, mb.filter, mb)
    if message.text == CREATE_NEW_FILTER:
        bot.send_message(
            message.chat.id,
            "Укажите тип писем, которые вы хотите получить:",
            reply_markup=mail_type_markup()
        )
        current_filter = ""
        filter_translation = ""
        bot.register_next_step_handler(message, add_type_filter, current_filter, filter_translation, mb)


def add_type_filter(message, current_filter, filter_translation, mb):
    current_filter += FILTER_TYPE[message.text]
    filter_translation += message.text
    bot.send_message(message.chat.id, "Фильтр добавлен", reply_markup=get_edit_filters_markup())
    bot.register_next_step_handler(message, filter_enricher, current_filter, filter_translation, mb)
    

def filter_enricher(message, current_filter, filter_translation, mb):
    if message.text == CANCEL_STR:
        bot.send_message(message.chat.id, "Отмена", reply_markup=get_default_markup())
        return
    if message.text == FILTERS_DONE:
        update_filter_in_db(
            user=User.objects.get(telegram_id=message.from_user.username),
            mb=mb,
            filter=current_filter,
            filter_translation=filter_translation
        )
        change_is_active(
            user=User.objects.get(telegram_id=message.from_user.username),
            mb=mb,
            is_active=True
        )
        show_messages(message, current_filter, mb)
    if message.text == SET_SENDER_STR:
        bot.send_message(message.chat.id, "Укажите желаемого отправителя", reply_markup=get_cancel_markup())
        new_filter_type = "FROM"
        filter_translation += " от "
        bot.register_next_step_handler(message, filter_enricher_ack, current_filter, new_filter_type, filter_translation, mb)
    if message.text == SET_DATE_FROM:
        bot.send_message(message.chat.id, "Укажите желаемую дату начала в формате 19-Sep-2022", reply_markup=get_cancel_markup())
        new_filter_type = "SENTSINCE"
        filter_translation += " после "
        bot.register_next_step_handler(message, filter_enricher_ack, current_filter, new_filter_type, filter_translation, mb)


def filter_enricher_ack(message, current_filter, new_filter_type, filter_translation, mb):
    if message.text == CANCEL_STR:
        bot.send_message(message.chat.id, "Отмена", reply_markup=get_edit_filters_markup())
        return
    current_filter += f' {new_filter_type} {message.text}'
    filter_translation += message.text
    bot.send_message(message.chat.id, "Фильтр добавлен", reply_markup=get_edit_filters_markup())
    bot.register_next_step_handler(message, filter_enricher, current_filter, filter_translation, mb)


def show_messages(message, filter, mb: Mailbox):
    print("showing emails ", mb.login, mb.password)
    bot.send_message(message.chat.id, "Фильтр включен", reply_markup=get_cancel_markup())
    while get_is_active(
            user=User.objects.get(telegram_id=message.from_user.username),
            mb=mb
        ):
        mail_server = get_mail_server(mb.login, mb.password, EMAILS["Yandex"]["host"], EMAILS["Yandex"]["port"], PASSWORD_AUTHORIZATION)
        texts = get_emails_by_filter(mail_server, filter, 1)
        for email in texts:
            soup = BeautifulSoup(email, features="html.parser")
            text = str(soup.get_text())
            while '  ' in text:
                text = text.replace('  ', ' ')
            while '\t\t' in text:
                text = text.replace('\t\t', '')
            while ' \n' in text:
                text = text.replace(' \n', '\n')
            while ' \t' in text:
                text = text.replace(' \t', '')
            while '\n\n' in text:
                text = text.replace('\n\n', '\n')
            bot.send_message(message.chat.id, text)
        bot.register_next_step_handler(message, end_filter_search, mb)
        time.sleep(5)


def end_filter_search(message, mb):
    change_is_active(
        user=User.objects.get(telegram_id=message.from_user.username),
        mb=mb,
        is_active=False
    )
    bot.send_message(message.chat.id, "Отмена", reply_markup=get_default_markup())


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
    if "@gmail.com" in message.text:
        bot.send_message(message.chat.id, f"Выберите тип авторизации", reply_markup=get_auth_types())
        bot.register_next_step_handler(message, get_type_of_auth, message.text)
    else:
        bot.send_message(message.chat.id, f"Введите пароль:", reply_markup=get_cancel_markup())
        bot.register_next_step_handler(message, save_mail, message.text)


def get_type_of_auth(message, mail_login):
    if message.text == OAUTH_AUTHORIZATION:
        bot.send_message(message.chat.id, f"Введите токен:", reply_markup=get_cancel_markup())
        bot.register_next_step_handler(message, save_mail, mail_login, OAUTH_AUTHORIZATION)
    else:
        bot.send_message(message.chat.id, f"Введите пароль:", reply_markup=get_cancel_markup())
        bot.register_next_step_handler(message, save_mail, mail_login, PASSWORD_AUTHORIZATION)


def save_mail(message, mail_login, auth_type):
    if message.text == CANCEL_STR:
        bot.send_message(message.chat.id, "Почта не добавлена", reply_markup=get_default_markup())
        return
    mail_password = message.text
    mail_id = ""
    logging.info(f"Login and password {mail_login}, {mail_password}")
    check_yandex_mail = get_mail_server(mail_login, mail_password, EMAILS["Yandex"]["host"], EMAILS["Yandex"]["port"], auth_type)
    check_google_mail = get_mail_server(mail_login, mail_password, EMAILS["Google"]["host"], EMAILS["Google"]["port"], auth_type)
    if check_yandex_mail:
        mail_id = "Yandex"
    elif check_google_mail:
        mail_id = "Google"
    else:
        bot.send_message(message.chat.id, f"Неправильный логин или пароль")
    if mail_id != "":
        try:
            user = User.objects.get(telegram_id=message.from_user.username)
            old_mailbox = Mailbox.objects.get(user=user)
            old_mailbox.delete()
            if auth_type == OAUTH_AUTHORIZATION:
                new_mailbox = Mailbox(mail_id=mail_id, login=mail_login, oauth_token=mail_password, user=user)
                new_mailbox.save()
            else:
                new_mailbox = Mailbox(mail_id=mail_id, login=mail_login, password=mail_password, user=user)
                new_mailbox.save()
            markup = get_default_markup()
            bot.send_message(message.chat.id, f"Почта успешно изменена, новый почтовый адрес - {mail_login}", reply_markup=markup)
        except Mailbox.DoesNotExist:
            if auth_type == OAUTH_AUTHORIZATION:
                new_mailbox = Mailbox(mail_id=mail_id, login=mail_login, oauth_token=mail_password,
                                      user=User.objects.get(telegram_id=message.from_user.username))
            else:
                new_mailbox = Mailbox(mail_id=mail_id, login=mail_login, password=mail_password,
                                      user=User.objects.get(telegram_id=message.from_user.username))
            new_mailbox.save()
            markup = get_default_markup()
            bot.send_message(message.chat.id, f"Почта {new_mailbox.login} успешно добавлена", reply_markup=markup)


class Command(BaseCommand):
    help = 'MailBot'

    def handle(self, *args, **options):
        bot.enable_save_next_step_handlers(delay=2)
        bot.load_next_step_handlers()
        bot.infinity_polling()
