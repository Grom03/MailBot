from django.db import models


class User(models.Model):
    telegram_id = models.CharField(
        verbose_name='Telegram ID',
        max_length=128
    )

    is_blocked_bot = models.BooleanField(default=False)

    class Meta:
        unique_together = (('telegram_id', 'is_blocked_bot'),)


class Mailbox(models.Model):
    mail_id = models.CharField(
        verbose_name='Name of mail',
        max_length=128
    )

    login = models.CharField(
        verbose_name='Login',
        max_length=128
    )

    password = models.CharField(
        verbose_name='Password',
        max_length=128,
        null=True
    )

    oauth_token = models.CharField(
        verbose_name='OAuth Token',
        max_length=128,
        null=True
    )

    filter = models.CharField(
        verbose_name='Filter',
        max_length=128,
        default='UNSEEN'
    )

    filter_translation = models.CharField(
        verbose_name='Filter translation',
        max_length=128,
        default='Непрочитанные письма'
    )

    is_active_search = models.BooleanField(
        verbose_name='Is Active Search',
        default=False
    )

    user = models.OneToOneField(User,
                                null=True,
                                blank=True,
                                related_name='mailbox',
                                related_query_name='mailbox',
                                on_delete=models.CASCADE)
