# -*- coding: utf-8 -*-
# @Time    : 2019/1/30 16:01
# @Author  : wjh
# @File    : urls.py
from django.urls import path
from . import views

app_name = 'course'

urlpatterns = [
    path('', views.course_list, name='index'),
    path('<int:course_id>/', views.CourseDetailViews.as_view(), name='course_detail'),
]