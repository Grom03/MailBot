from django.core.management.base import BaseCommand
from django.conf import settings
from telebot import TeleBot

class Command(BaseCommand):
    help = 'MailBot'

    def handle(self, *args, **options):
        pass
