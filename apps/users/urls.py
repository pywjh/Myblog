# -*- coding: utf-8 -*-
# @Time    : 2019/1/29 15:14
# @Author  : wjh
# @File    : urls.py
from django.urls import path

from . import views

app_name = 'users'

urlpatterns = [
    path('login/', views.LoginViews.as_view(), name='login'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
]