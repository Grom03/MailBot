from django.db import models


class User(models.Model):
    telegram_id = models.CharField(
        verbose_name='Telegram ID',
        related_query_name='telegram_id',
        related_name='telegram_id',
        max_length=128
    )

    is_blocked_bot = models.BooleanField(default=False)

    class Meta:
        unique_together = (('telegram_id', 'is_blocked_bot'),)


class Mailbox(models.Model):
    mail_id = models.CharField(
        verbose_name='Name of mail',
        related_query_name='mail_id',
        related_name='mail_id',
        max_length=128
    )

    login = models.CharField(
        verbose_name='Login',
        related_query_name='login',
        related_name='login',
        max_length=128
    )

    password = models.CharField(
        verbose_name='Password',
        related_query_name='password',
        related_name='password',
        max_length=128
    )

    user = models.ForeignKey(User,
                             null=True,
                             blank=True,
                             related_name='mailboxes',
                             related_query_name='mailboxes',
                             on_delete=models.SET_NULL)

    class Meta:
        unique_together = (('user', 'mail_id', 'login', 'password'),)
