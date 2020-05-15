from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager as _UserManage


class UserManager(_UserManage):
    """
       define user manager for modifing 'no need email'
       when 'python manager.py createsuperuser
    """
    def create_superuser(self, username, password, email=None, **extra_fields):
        super(UserManager, self).create_superuser(username=username,
                                                  password=password,
                                                  email=email,
                                                  **extra_fields)


class Users(AbstractUser):
    """
    add mobile and email_active fields to Django's Users models
    """

    objects = UserManager()
    # A list of the field names that will be prompted for
    # when creating a user via the createsuperuser management command.

    REQUIRED_FIELDS = ['mobile']

    mobile = models.CharField(max_length=11,
                              unique=True,
                              help_text='手机号',
                              verbose_name='手机号',
                              error_messages={
                                  'unique': '此手机号已经注册'
                              })
    email_active = models.BooleanField(default=False, verbose_name='邮箱验证状态')

    class Meta:
        db_table = 'tb_users'
        verbose_name = '用户'
        verbose_name_plural = verbose_name


    def __str__(self):
        return self.username










