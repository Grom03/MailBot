from django.db import models

class MailAuth(models.Model):
    telegram_id = models.CharField(
        verbose_name='ID в телеграмм',
        max_length=128
    )
    mail_id = models.CharField(
        verbose_name='Название почты',
        max_length=128
    )
    mail_login = models.CharField(
        verbose_name='Логин в почте',
        max_length=128
    )
    mail_password = models.CharField(
        verbose_name='Пароль от почты',
        max_length=128
    )

    class Meta:
        unique_together=(('telegram_id', 'mail_id', 'mail_login'),)
