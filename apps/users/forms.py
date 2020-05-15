#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re

from django import forms
from django.contrib.auth import login
from django.db.models import Q
from django_redis import get_redis_connection

from verifications.constants import SMS_CODE_NUMS
from .models import Users
from . import constants



class RegisterForm(forms.Form):
    """
    验证注册页面的数据是否合法
    用户名、密码、确认密码、手机号、短信验证码
    """
    username = forms.CharField(label='用户名', max_length=20, min_length=5,
                               error_messages={"min_length": "用户名长度要大于5", "max_length": "用户名长度要小于20",
                                               "required": "用户名不能为空"}
                               )
    password = forms.CharField(label='密码', max_length=20, min_length=6,
                               error_messages={"min_length": "密码长度要大于6", "max_length": "密码长度要小于20",
                                               "required": "密码不能为空"}
                               )
    password_repeat = forms.CharField(label='确认密码', max_length=20, min_length=6,
                                      error_messages={"min_length": "密码长度要大于6", "max_length": "密码长度要小于20",
                                                      "required": "密码不能为空"}
                                      )
    mobile = forms.CharField(label='手机号', max_length=11, min_length=11,
                             error_messages={"min_length": "手机号长度有误", "max_length": "手机号长度有误",
                                             "required": "手机号不能为空"})

    sms_code = forms.CharField(label='短信验证码', max_length=SMS_CODE_NUMS, min_length=SMS_CODE_NUMS,
                               error_messages={"min_length": "短信验证码长度有误", "max_length": "短信验证码长度有误",
                                               "required": "短信验证码不能为空"})

    def clean_mobile(self):
        """
        手机号单独再验证
        1. 判断手机号码是否符合规则
        2. 判断手机号是否已经注册
        """
        tel = self.cleaned_data.get('mobile')
        # re.match 尝试从字符串的起始位置匹配一个模式，如果不是起始位置匹配成功的话，match()就返回none
        if not re.match(r"^1[3-9]\d{9}$", tel):
            raise forms.ValidationError("手机号码格式不正确")

        # 去数据库里面确认电话号码是否重复
        if Users.objects.filter(mobile=tel).exists():
            raise forms.ValidationError("手机号已注册，请重新输入！")

        return tel

    def clean(self):
        """
        获取所有的字段进行再验证
        1. 获取密码和确认密码两个字段，判断输入的两次密码是否相同
        2. 获取用户输入的短信验证码和存入redis中的短信验证码是否相同
            2.1 redis中的短信验证码需要擦创建钥匙取出数据
        """
        # 获取所有的字段信息对象
        cleaned_data = super().clean()
        passwd = cleaned_data.get('password')
        passwd_repeat = cleaned_data.get('password_repeat')

        if passwd != passwd_repeat:
            # 如果用户输入的密码和确认密码不一致的话就报错
            raise forms.ValidationError("两次密码不一致")

        # 获取电话和短信验证码
        tel = cleaned_data.get('mobile')
        sms_text = cleaned_data.get('sms_code')

        # 建立redis连接
        redis_conn = get_redis_connection(alias='verify_codes')
        # 构建短信钥匙
        sms_fmt = "sms_{}".format(tel).encode('utf-8')
        # 取出短信验证码
        real_sms = redis_conn.get(sms_fmt)

        # 校验短信验证码真假
        if (not real_sms) or (sms_text != real_sms.decode('utf-8')):
            raise forms.ValidationError("短信验证码错误")


class LoginForm(forms.Form):
    '''
    验证用户登陆时输入的信息是否合法
    用户名、密码、是否点击记住我
    '''
    user_account = forms.CharField()
    password = forms.CharField(label='密码', max_length=20, min_length=6,
                               error_messages={
                                   'max_length': '密码长度不得大于20',
                                   'min_length': '密码长度不得小于6',
                                   'required': ''
                                               '密码不能为空'
                               })
    remember_me = forms.BooleanField(required=False) # 默认设置required为False，不然可能会有Bug

    def __init__(self, *args, **kwargs):
        '''
        获取views传来的request对象
        '''
        self.request = kwargs.pop('request', None)
        super(LoginForm, self).__init__(*args, **kwargs)

    def clean_user_account(self):
        '''
        对user_account进行再校验
        :return  user_info
        '''
        # 获取用户登陆的账号（可能是用户名，可能是电话号码）
        user_info = self.cleaned_data.get('user_account')
        if not user_info:
            raise forms.ValidationError("用户名不能为空")

        if not re.match(r'^1[3-9]\d{9}$]', user_info) and (len(user_info) < 5 or len(user_info) > 20):
            raise forms.ValidationError('用户名格式不正确，请重新输入')

        return user_info

    def clean(self):
        '''
        校验所有的字段信息
        :return:
        '''
        clean_data = super().clean()
        # 获取清洗之后的用户账号
        user_info = clean_data.get('user_account')
        # 获取清洗之后的密码
        passwd = clean_data.get('password')
        hold_login = clean_data.get('remember_me')

        # 再form表单中实现登陆逻辑
        user_queryset = Users.objects.filter(Q(mobile=user_info) | Q(username=user_info))
        if user_queryset:
            user = user_queryset.first()
            if user.check_password(passwd):
                if hold_login: # redis中保存session信息
                    self.request.session.set_expiry(constants.USER_SESSION_EXPIRES)  # 对应时间之后过期
                else:
                    self.request.session.set_expiry(0)  # 关闭窗口自动清除   None是用不清除
                login(self.request, user)
            else:
                raise forms.ValidationError("密码不正确，请重新输入")
        else:
            raise forms.ValidationError("用户名不存在，请确认账号信息是否正确")
