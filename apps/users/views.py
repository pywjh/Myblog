import json
import logging

from django.contrib.auth import login, logout
from django.shortcuts import render, redirect, reverse
from django.views import View

from utils.json_fun import to_json_data
from utils.res_code import Code, error_map
from .forms import RegisterForm
from .models import Users
from .forms import LoginForm

# 导入日志器
logger = logging.getLogger('django')

class LoginViews(View):
    '''
    handle login
    # /users/login/
    '''

    def get(self, request):
        '''处理get请求，返回登陆页面'''
        return render(request, 'users/login.html')

    def post(self, request):
        '''处理post请求，实现登陆逻辑'''
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 将json转化为dict
        dict_data = json.loads(json_data.decode('utf8'))
        # 将request对象传给forms，直接再forms中进行登陆操作
        form = LoginForm(data=dict_data, request=request)
        if form.is_valid():
            return to_json_data(errmsg="恭喜您，登陆成功!")
        else:
            # 定义一个错误的信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str = '/'.join(err_msg_list)
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)


class RegisterView(View):
    """
    user register
    /users/register/
    # 1、创建一个类
    """
    def get(self, request):
        """
        handle get request, render register page.
        # 2、创建get方法
        :param request:
        :return:
        """
        return render(request, 'users/register.html')

    def post(self, request):
        """
        handle post request, verify form data
        # 3、创建post方法
        :param request:
        :return:
        """
        # 4、获取前端传过来的参数
        try:
            json_data = request.body
            if not json_data:
                return to_json_data(errno=Code.PARAMERR, errmsg="参数为为空，请重新输入！")
            dict_data = json.loads(json_data.decode('utf8'))
        except Exception as e:
            logger.info('错误信息：\n{}'.format(e))
            return to_json_data(errno=Code.UNKOWNERR, errmsg=error_map[Code.UNKOWNERR])

        # 5、校验参数
        form = RegisterForm(data=dict_data)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            mobile = form.cleaned_data.get('mobile')

            # 6、将用户信息保存到数据库
            user = Users.objects.create_user(username=username, password=password, mobile=mobile)
            # user.mobile = mobile
            # user.save()
            login(request, user)
            return to_json_data(errmsg="恭喜您，注册成功！")
        else:
            # 7、将结果返回给前端
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
                # print(item[0].get('message'))   # for test
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串

            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)


class LogoutView(View):
    '''
    用户退出登陆逻辑处理
    # /users/logout/
    '''
    def get(self, request):
        '''
        user logout code
        :return: re
        '''
        logout(request)
        return redirect(reverse('users:login'))




