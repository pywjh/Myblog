# -*- coding: utf-8 -*-
# @Time    : 2019/1/30 16:01
# @Author  : wjh
# @File    : urls.py
from django.urls import path
from . import views

app_name = 'admin'

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'), # admin后台站点首页


    path('news/', views.NewsManageView.as_view(), name='news_manage'), # 文章管理
    path('news/<int:news_id>/', views.NewsEditView.as_view(), name='news_edit'), # 文章编辑
    path('news/pub/', views.NewsPubView.as_view(), name='news_pub'), # 文章发布
    path('news/images/', views.NewsUploadImage.as_view(), name='upload_image'), # 图片上传服务器FastDFS


    path('banners/', views.BannerManageView.as_view(), name='banner_manage'), # 文章轮播图
    path('banners/<int:banner_id>/', views.BannerEditView.as_view(), name='banners_edit'), # 轮播图编辑操作（更新和删除）
    path('banners/add/', views.BannerAddView.as_view(), name='banners_add'), # 添加轮播图的页面渲染


    path('token/', views.UploadToken.as_view(), name='upload_token'), # 七牛云上传图片需要调用token


    path('tags/', views.TagsManageView.as_view(), name='tags'), # 标签管理
    path('tags/<int:tag_id>/', views.TagEditView.as_view(), name='tag_edit'), # 标签编辑
    path('tags/<int:tag_id>/news/', views.NewsByTagIdView .as_view(), name='news_by_tagid'), #


    path('hotnews/', views.HotNewsManageView.as_view(), name='hotnews_manage'), # 热门文章管理
    path('hotnews/add/', views.HotNewsAddView.as_view(), name='hotnews_add'), # 热门文章添加
    path('hotnews/<int:hotnews_id>/', views.HotNewsEditView.as_view(), name='hotnews_edit'), # 热门文章编辑


    path('docs/', views.DocsManageView.as_view(), name='doc_manage'), # 文档管理页面
    path('docs/<int:doc_id>/', views.DocsEditView.as_view(), name='docs_edit'), # 文档更新页面
    path('docs/files/', views.DocsUploadFile.as_view(), name='upload_file'), # 文档上传功能
    path('docs/pub/', views.DocsPubView.as_view(), name='docs_pub'),


    path('courses/', views.CoursesManageView.as_view(), name='course_manage'),
    path('courses/<int:course_id>/', views.CoursesEditView.as_view(), name='course_edit'),
    path('courses/pub/', views.CoursesPubViews.as_view(), name='course_pub'),


    path('groups/', views.GroupManageView.as_view(), name='groups_manage'),
    path('groups/<int:group_id>/', views.GroupsEditView.as_view(), name='groups_edit'),
    path('groups/add/', views.GroupsAddView.as_view(), name='groups_add'),

    path('users/', views.UserManageView.as_view(), name='users_manage'),
    path('users/<int:user_id>/', views.UserEditView.as_view(), name='users_edit'),



]