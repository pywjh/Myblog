# -*- coding: utf-8 -*-
# @Time    : 2019/1/30 16:47
# @Author  : wjh
# @File    : urls.py
from django.urls import path

from . import views

app_name = 'doc'

urlpatterns = [
    path('doc_download/', views.doc_index, name='index'),
    path('<int:doc_id>/', views.DocDownload.as_view(), name='doc_download'),
]