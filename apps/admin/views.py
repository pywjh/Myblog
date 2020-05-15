import json
import logging
import qiniu

from collections import OrderedDict
from datetime import datetime
from django.core.paginator import Paginator, EmptyPage
from django.http import Http404, JsonResponse
from django.shortcuts import render
from urllib.parse import urlencode
from django.views import View
from django.db.models import Count
from django.conf import settings
from django.contrib.auth.models import Group, ContentType, Permission

from . import forms
from . import constants
from news import models
from doc.models import Doc
from course.models import Course, CourseCategory, Teacher
from scripts import paginator_script
from utils.json_fun import to_json_data
from utils.res_code import Code, error_map
from utils.secrets import qiniu_secret_info
from utils.fastdfs.fdfs import FDFS_Client
from users.models import Users


logger = logging.getLogger('django')


class IndexView(View):
    '''
    后台首页
    admin index view
    route: /admin/
    '''
    def get(self, request):
        return render(request, 'admin/index/index.html', locals())


class TagsManageView(View):
    '''
    标签管理
    create tags manage view
    route: /admin/tags/
    '''
    def get(self, request):
        '''
        文章标签分类的页面渲染
        :param request:
        :return:
        '''
        # tags = models.Tag.objects.values('id', 'name').annotate(num_news=Count('news'))
        # <QuerySet [{'id': 6, 'name': 'python框架', 'num_news': 63}, {'id': 5, 'name': 'Linux教程', 'num_news': 198}, {'id': 4, 'name': 'PythonGUI', 'num_news': 43}, {'id': 3, 'name': 'Python函数', 'num_news': 26}, {'id': 2, 'name': 'Python高级', 'num_news': 258}, {'id': 1, 'name': 'Python基础', 'num_news': 301}]>
        tags = models.Tag.objects.values('id', 'name').annotate(num_news=Count('news')).filter(is_delete=False).order_by('-num_news')
        return render(request, 'admin/news/tags_manage.html', locals())

    def post(self, request):
        '''
        添加标签
        '''
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf-8'))
        tag_name = dict_data.get('name')
        if tag_name and tag_name.strip():
            # get_or_create获取或查找，
            # 如果存在，返回数据结果以及为创建的布尔值False
            # 不存在，新建，并返回True
            tag_tuple = models.Tag.objects.get_or_create(name=tag_name)
            tag_instance, tag_created_bolean = tag_tuple
            new_tag_dict = {
                'id': tag_instance.id,
                'name': tag_instance.name
            }
            return to_json_data(errmsg="标签创建成功", data=new_tag_dict) if tag_created_bolean else to_json_data(errno=Code.DATAEXIST, errmsg="标签名已存在")
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg="标签名为空")


class TagEditView(View):
    '''
    标签编辑
    create tag edit view
    route: /admin/tags/<int:tag_id>/
    '''
    def delete(self, request, tag_id):
        tag = models.Tag.objects.only('id').filter(id=tag_id).first()
        if tag:
            # 真删
            # tag.delete()
            tag.is_delete = True
            tag.save(update_fields=['is_delete'])
            return to_json_data(errmsg="标签删除成功")
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg="需要删除的标签不存在")

    def put(self, request, tag_id):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 将json转化为dict
        dict_data = json.loads(json_data.decode('utf8'))
        tag_name = dict_data.get('name')
        tag = models.Tag.objects.only('id').filter(id=tag_id).first()
        if tag:
            if tag_name:
                tag_name = tag_name.strip()
                if not models.Tag.objects.only('id').filter(name=tag_name).exists():
                    tag.name = tag_name
                    tag.save(update_fields=['name'])
                    return to_json_data(errmsg="标签更新成功")
                else:
                    return to_json_data(errno=Code.DATAEXIST, errmsg="标签名已存在")
            else:
                return to_json_data(errno=Code.PARAMERR, errmsg="标签名为空")

        else:
            return to_json_data(errno=Code.PARAMERR, errmsg="需要更新的标签不存在")


class HotNewsManageView(View):
    '''
    热门新闻管理
    create hot news manage view
    route: /admin/hotnews/
    '''
    def get(self, request):
        hot_news = models.HotNews.objects.select_related('news__tag').only('news_id', 'news__title', 'news__tag__name', 'priority').filter(is_delete=False).order_by('priority', '-news__clicks')[0: constants.SHOW_HOTNEWS_COUNT]
        return render(request, 'admin/news/news_hot.html', locals())


class HotNewsEditView(View):
    '''
    热门新闻编辑
    create hot news edit's view
    route: /admin/hotnews/<int:hotnews_id>/
    '''
    def delete(self, request, hotnews_id):
        hotnews = models.HotNews.objects.only('id').filter(id=hotnews_id).first()
        if hotnews:
            hotnews.is_delete = True
            hotnews.save(update_fields=['is_delete'])
            return to_json_data(errmsg='热门文章删除成功')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='需要删除的热门文章不存在')

    def put(self, request, hotnews_id):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 将json转化为dict
        dict_data = json.loads(json_data.decode('utf8'))

        try:
            priority = int(dict_data.get('priority'))
            priority_list = [i for i, _ in models.HotNews.PRI_CHOICES]
            # 如果需要修改的优先级不在范围内
            if priority not in priority_list:
                return to_json_data(errno=Code.PARAMERR, errmsg='热门文章的优先级设置错误')
        except Exception as e:
            logger.info('热门文章优先级异常：\n{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='热门文章的优先级设置错误')

        hotnews = models.HotNews.objects.only('id').filter(id=hotnews_id).first()
        if not hotnews:
            # 如果所修改的文章本来就不存在
            return to_json_data(errno=Code.PARAMERR, errmsg="需要更新的热门文章不存在")

        if hotnews.priority == priority:
            # 修改的等级未改变
            return to_json_data(errno=Code.PARAMERR, errmsg="热门文章的优先级未改变")

        # 没有问题
        hotnews.priority = priority
        hotnews.save(update_fields=['priority'])
        return to_json_data(errmsg='热门文章更新成功')


class HotNewsAddView(View):
    '''
    get: 渲染热门新闻添加视图的下拉标签和标签等级
    create hot news add's view
    route: /admin/hotnews/add/
    '''
    def get(self, request):
        tags = models.Tag.objects.values('id', 'name').annotate(num_news=Count('news')).filter(is_delete=False).order_by('-num_news', 'update_time')
        # 优先级列表
        # priority_list = {K: v for k, v in models.HotNews.PRI_CHOICES}
        priority_dict = OrderedDict(models.HotNews.PRI_CHOICES)
        return render(request, 'admin/news/news_hot_add.html', locals())

    def post(self, request):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 将json转化为dict
        dict_data = json.loads(json_data.decode('utf8'))

        try:
            news_id = int(dict_data.get('news_id'))
        except Exception as e:
            logger.info('前端传过来的文章id参数异常：\n{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='文章不存在')

        if not models.News.objects.filter(id=news_id).exists():
            return to_json_data(errno=Code.PARAMERR, errmsg='文章不存在')

        try:
            priority = int(dict_data.get('priority'))
            priority_list = [i for i, _ in models.HotNews.PRI_CHOICES]
            if priority not in priority_list:
                return to_json_data(errno=Code.PARAMERR, errmsg='热门文章的优先级设置错误')
        except Exception as e:
            logger.info('热门文章优先级异常：\n{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='热门文章的优先级设置错误')

        # 创建热门文章
        hotnews_tuple = models.HotNews.objects.get_or_create(news_id=news_id)
        hotnews, is_created = hotnews_tuple
        hotnews.priority = priority # 修改优先级
        hotnews.save(update_fields=['priority'])
        return to_json_data(errmsg='热门文章创建成功')


class NewsByTagIdView(View):
    '''
    由下拉菜单选定标签，来确定新闻的选取范围
    route: /admin/tags/<int:tag_id>/news/
    '''
    def get(self, request, tag_id):
        newses = models.News.objects.values('id', 'title').filter(is_delete=False, tag_id=tag_id)
        news_list = [i for i in newses]

        return to_json_data(data={
            'news': news_list
        })


class NewsManageView(View):
    '''
    文章管理
    create new manage view
    route: /admin/news/
    '''
    def get(self, request):
        '''
        获取文章列表信息
        '''
        tags = models.Tag.objects.only('id', 'name').filter(is_delete=False)
        newses = models.News.objects.only('id', 'title', 'author__username', 'tag__name', 'update_time').select_related('author', 'tag').filter(is_delete=False)

        # 通过时间进行过滤
        try:
            start_time = request.GET.get('start_time', '')
            start_time = datetime.strptime(start_time, '%Y/%m/%d') if start_time else ''

            end_time = request.GET.get('end_time', '')
            end_time = datetime.strptime(end_time, '%Y/%m/%d') if end_time else ''
        except Exception as e:
            logger.info("用户输入的时间有误：\n{}".format(e))
            start_time = end_time = ''

        if start_time and not end_time:
            newses = newses.filter(update_time__lte=start_time)
        if end_time and not start_time:
            newses = newses.filter(update_time__gte=end_time)

        if start_time and end_time:
            newses = newses.filter(update_time__range=(start_time, end_time))

        # 通过title进行过滤
        title = request.GET.get('title', '')
        if title:
            newses = newses.filter(title__icontains=title)

        # 通过作者名进行过滤
        author_name = request.GET.get('author_name', '')
        if author_name:
            newses = newses.filter(author__username__icontains=author_name)

        # 通过标签id进行过滤
        try:
            tag_id = int(request.GET.get('tag_id', 0))
        except Exception as e:
            logger.info('标签错误：\n{}'.format(e))
            tag_id = 0

        newses = newses.filter(is_delete=False, tag_id=tag_id) or newses.filter(is_delete=False)

        # 获取第几页内容
        try:
            page = int(request.GET.get('page', 1))
        except Exception as e:
            logger.info("当前页数错误：\n{}".format(e))
            page = 1
        paginator = Paginator(newses, constants.PER_PAGE_NEWS_COUNT)
        try:
            news_info = paginator.page(page)
        except EmptyPage:
            # 若用户访问的页数大于实际页数，则返回最后一页数据
            logging.info("用户访问的页数大于总页数。")
            news_info = paginator.page(paginator.num_pages)

        paginator_data = paginator_script.get_paginator_data(paginator, news_info)
        start_time = start_time.strftime('%Y/%m/%d') if start_time else ''
        end_time = end_time.strftime('%Y/%m/%d') if end_time else ''
        context = {
            'news_info': news_info,
            'tags': tags,
            'paginator': paginator,
            'start_time': start_time,
            "end_time": end_time,
            "title": title,
            "author_name": author_name,
            "tag_id": tag_id,
            "other_param": urlencode({
                "start_time": start_time,
                "end_time": end_time,
                "title": title,
                "author_name": author_name,
                "tag_id": tag_id,
            })
        }
        context.update(paginator_data)
        return render(request, 'admin/news/news_manage.html', context=context)


class NewsEditView(View):
    '''
    文章编辑
    '''
    def get(self, request, news_id):
        '''
        获取待编辑的文章
        '''
        news = models.News.objects.filter(is_delete=False, id=news_id).first()
        if news:
            tags = models.Tag.objects.only('id', 'name').filter(is_delete=False)
            context = {
                'tags': tags,
                'news': news
            }
            return render(request, 'admin/news/news_pub.html', locals())
        else:
            raise Http404('需要更新的文章不存在！')

    def delete(self, request, news_id):
        '''
        删除文章
        '''
        news = models.News.objects.only('id').filter(id=news_id).first()
        if news:
            news.is_delete = True
            news.save(update_fields=['is_delete'])
            return to_json_data(errmsg='文章删除成功')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='需要删除的文章不存在')

    def put(self, request, news_id):
        '''
        更新文章
        '''
        news = models.News.objects.filter(is_delete=False, id=news_id).first()
        if not news:
            return to_json_data(errno=Code.PARAMERR, errmsg='需要更新的文章不存在')

        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 将json转化为dict
        dict_data = json.loads(json_data.decode('utf8'))

        form = forms.NewsPubForm(data=dict_data)
        if form.is_valid():
            news.title = form.cleaned_data.get('title')
            news.digest = form.cleaned_data.get('digest')
            news.content = form.cleaned_data.get('content')
            news.image_url = form.cleaned_data.get('image_url')
            news.tag = form.cleaned_data.get('tag')
            news.save()
            return to_json_data(errmsg='文章更新成功')
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串

            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)


class NewsPubView(View):
    """
    新增文章
    """
    def get(self, request):
        """
        获取文章标签
        """
        tags = models.Tag.objects.only('id', 'name').filter(is_delete=False)

        return render(request, 'admin/news/news_pub.html', locals())

    def post(self, request):
        """
        新增文章
        """
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 将json转化为dict
        dict_data = json.loads(json_data.decode('utf8'))

        form = forms.NewsPubForm(data=dict_data)
        if form.is_valid():
            news_instance = form.save(commit=False)
            news_instance.author_id = request.user.id
            # news_instance.author_id = 1     # for test
            news_instance.save()
            return to_json_data(errmsg='文章创建成功')
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串

            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)


class NewsUploadImage(View):
    """
    图片文件上传FDFS
    """
    def post(self, request):
        image_file = request.FILES.get('image_file')
        if not image_file:
            logger.info('从前端获取图片失败')
            return to_json_data(errno=Code.NODATA, errmsg='从前端获取图片失败')

        if image_file.content_type not in ('image/jpeg', 'image/png', 'image/gif'):
            return to_json_data(errno=Code.DATAERR, errmsg='不能上传非图片文件')

        try:
            image_ext_name = image_file.name.split('.')[-1]
        except Exception as e:
            logger.info('图片拓展名异常：{}'.format(e))
            image_ext_name = 'jpg'

        try:
            upload_res = FDFS_Client.upload_by_buffer(image_file.read(), file_ext_name=image_ext_name)
        except Exception as e:
            logger.error('图片上传出现异常：{}'.format(e))
            return to_json_data(errno=Code.UNKOWNERR, errmsg='图片上传异常')
        else:
            if upload_res.get('Status') != 'Upload successed.':
                logger.info('图片上传到FastDFS服务器失败')
                return to_json_data(Code.UNKOWNERR, errmsg='图片上传到服务器失败')
            else:
                image_name = upload_res.get('Remote file_id')
                image_url = settings.FASTDFS_SERVER_DOMAIN + image_name
                return to_json_data(data={'image_url': image_url}, errmsg='图片上传成功')


class UploadToken(View):
    '''
    七牛云上传图片
    :return image url
    '''
    def get(self, request):
        access_key = qiniu_secret_info.QI_NIU_ACCESS_KEY
        secret_key = qiniu_secret_info.QI_NIU_SECRET_KEY
        bucket_name = qiniu_secret_info.QI_NIU_BUCKET_NAME
        # 构建鉴权对象
        q = qiniu.Auth(access_key, secret_key)
        token = q.upload_token(bucket_name)

        return JsonResponse({'uptoken': token})


class BannerManageView(View):
    '''
    轮播图管理
    route: /banners/
    '''
    def get(self, request):
        priority_dict = OrderedDict(models.Banner.PRI_CHOICES)
        banners = models.Banner.objects.only('image_url', 'priority').filter(is_delete=False)
        return render(request, 'admin/news/news_banner.html', locals())


class BannerEditView(View):
    '''
    编辑轮播图
    route: /banner/<int:banner_id>/
    '''
    def delete(self, request, banner_id):
        '''
        删除轮播图
        '''
        banner = models.Banner.objects.only('id').filter(id=banner_id).first()
        if banner:
            banner.is_delete = True
            banner.save(update_fields=['is_delete'])
            return to_json_data(errmsg='轮播图删除有成功')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='需要删除的轮播图不存在')

    def put(self, request, banner_id):
        banner = models.Banner.objects.only('id').filter(id=banner_id).first()
        if not banner:
            return to_json_data(errno=Code.PARAMERR, errmsg='需要更新的轮播图不存在')
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 将json转化为dict
        dict_data = json.loads(json_data.decode('utf-8'))

        # 获取ajax传递过来的优先级，图片URL
        try:
            priority = int(dict_data.get('priority'))
            priority_list = [i for i, _ in models.Banner.PRI_CHOICES]
            if priority not in priority_list:
                return to_json_data(errno=Code.PARAMERR, errmsg='轮播图的优先级设置错误')
        except Exception as e:
            logger.info('轮播图优先级异常：\n{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='轮播图的优先级设置错误')

        image_url = dict_data.get('image_url')
        if not image_url:
            return to_json_data(errno=Code.PARAMERR, errmsg='轮播图url为空')

        if banner.priority == priority and banner.image_url == image_url:
            return to_json_data(errno=Code.PARAMERR, errmsg='轮播图的参数未发生改变')

        banner.priority = priority
        banner.image_url = image_url
        banner.save(update_fields=['priority', 'image_url'])
        return to_json_data(errmsg='轮播图更新成功')


class BannerAddView(View):
    '''
    添加轮播图
    route: /banners/add/
    '''

    def get(self, request):
        tags = models.Tag.objects.values('id', 'name').annotate(num_news=Count('news')). \
            filter(is_delete=False).order_by('-num_news', 'update_time')
        # 优先级列表
        # priority_list = {K: v for k, v in models.Banner.PRI_CHOICES}
        priority_dict = OrderedDict(models.Banner.PRI_CHOICES)

        return render(request, 'admin/news/news_banner_add.html', locals())

    def post(self, request):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 将json转化为dict
        dict_data = json.loads(json_data.decode('utf-8'))

        try:
            news_id = int(dict_data.get('news_id'))
        except Exception as e:
            logger.info('前端传过的文章id参数异常：\n{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='参数错误')

        if not models.News.objects.filter(id=news_id).exists():
            return to_json_data(errno=Code.PARAMERR, errmsg='文章不存在')

        try:
            priority = int(dict_data.get('priority'))
            priority_list = [i for i, _ in models.Banner.PRI_CHOICES]
            if priority not in priority_list:
                return to_json_data(errno=Code.PARAMERR, errmsg='轮播图的优先级设置错误')
        except Exception as e:
            logger.info('轮播图优先级异常：\n{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='轮播图的优先级设置错误')

        # 获取轮播图url
        image_url = dict_data.get('image_url')
        if not image_url:
            return to_json_data(errno=Code.PARAMERR, errmsg='轮播图url不能为空')

        # 创建轮播图
        banners_tuple = models.Banner.objects.get_or_create(news_id=news_id)
        banner, is_created = banners_tuple

        banner.priority = priority
        banner.image_url = image_url
        banner.save(update_fields=['priority', 'image_url'])
        return to_json_data(errmsg='轮播图创建成功')


class DocsManageView(View):
    """
    后台文档管理视图
    route: /admin/docs/
    """
    def get(self, request):
        docs = Doc.objects.only('title', 'create_time').filter(is_delete=False)
        return render(request, 'admin/doc/docs_manage.html', locals())


class DocsEditView(View):
    '''
    文档编辑视图
    route: /admin/docs/<int:doc_id>/
    '''
    def get(self, request, doc_id):
        '''
        渲染文档修改页面
        '''
        doc = Doc.objects.filter(is_delete=False, id=doc_id).first()
        if doc:
            tags = Doc.objects.only('id', 'name').filter(is_delete=False)
            context = {
                'doc': doc
            }
            return render(request, 'admin/doc/docs_pub.html', locals())

    def delete(self, request, doc_id):
        '''
        删除文档
        '''
        doc = Doc.objects.filter(is_delete=False, id=doc_id).first()
        if doc:
            doc.is_delete = True
            doc.save(update_fields=['is_delete'])
            return to_json_data(errmsg='文档删除成功')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='需要删除的文件不存在')

    def put(self, request, doc_id):
        '''
        更新文档
        '''
        doc = Doc.objects.filter(id=doc_id, is_delete=False).first()
        if not doc:
            return to_json_data(errno=Code.NODATA, errmsg='需要更新的文件不存在')

        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 将json转化为dict
        dict_data = json.loads(json_data.decode('utf-8'))

        form  = forms.DocsPubForm(data=dict_data)
        if form.is_valid():
            docs_instance = form.save(commit=False)
            docs_instance.author_id = request.user.id
            docs_instance.save()
            return to_json_data(errmsg='文档创建成功')
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)


class DocsUploadFile(View):
    '''
    文档上传视图
    route: /admin/docs/files/
    '''
    def post(self, request):
        text_file = request.FILES.get('text_file')
        if not text_file:
            logger.info('从前端获取文件失败')
            return to_json_data(errno=Code.NODATA, errmsg='从前端获取文件失败')

        # https://developer.mozilla.org/zh-CN/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Complete_list_of_MIME_types
        if text_file.content_type not in ('application/msword', 'application/octet-stream', 'application/pdf', 'application/zip', 'text/plain', 'application/x-rar', 'application/x-abiword'):
            return to_json_data(errno=Code.DATAERR, errmsg='不能上传非文本文件')

        try:
            text_ext_name = text_file.name.split('.')[-1]
        except Exception as e:
            logger.info('文件拓展名异常：{}'.format(e))
            text_ext_name = 'pdf'

        try:
            upload_res = FDFS_Client.upload_by_buffer(text_file.read(), file_ext_name=text_ext_name)
        except Exception as e:
            logger.error('文件上传出现异常：{}'.format(e))
            return to_json_data(errno=Code.UNKOWNERR, errmsg='文件上传异常')
        else:
            if upload_res.get('Status') != 'Upload successed.':
                logger.info('文件上传到FastDFS服务器失败')
                return to_json_data(Code.UNKOWNERR, errmsg='文件上传到服务器失败')
            else:
                text_name = upload_res.get('Remote file_id')
                text_url = settings.FASTDFS_SERVER_DOMAIN + text_name
                return to_json_data(data={'text_file': text_url},errmsg='文件上传成功')


class DocsPubView(View):
    '''
    文档发布视图
    route: /admin/news/pub/
    '''
    def get(self, request):
        return render(request, 'admin/doc/docs_pub.html', locals())

    def post(self, request):
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 将json转化为dict
        dict_data = json.loads(json_data.decode('utf8'))

        form = forms.DocsPubForm(data=dict_data)
        if form.is_valid():
            docs_instance = form.save(commit=False)
            docs_instance.author_id = request.user.id
            docs_instance.save()
            return to_json_data(errmsg='文档创建成功')
        else:
            # 定义一个错误列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str = '/'.join(err_msg_list)
            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)


class CoursesEditView(View):
    '''
    route: /admin/courses/<int:course_id>/
    '''
    def get(self, request, course_id):
        """
        渲染课程管理页面
        """
        course = Course.objects.filter(is_delete=False, id=course_id).first()
        if course:
            teachers = Teacher.objects.only('name').filter(is_delete=False)
            categories = CourseCategory.objects.only('name').filter(is_delete=False)
            return render(request, 'admin/course/courses_pub.html', locals())
        else:
            raise Http404('需要更新的课程不存在！')

    def delete(self, request, course_id):
        '''
        删除课程
        '''
        course = Course.objects.filter(is_delete=False, id=course_id).first()
        if course:
            course.is_delete = True
            course.save(update_fields=['is_delete'])
            return to_json_data(errmsg="课程删除成功")
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg="需要删除的课程不存在")

    def put(self, request, course_id):
        '''
        更新课程
        '''
        course = Course.objects.filter(is_delete=False, id=course_id).first()
        if not course:
            return to_json_data(errno=Code.NODATA, errmsg='需要更新的课程不存在')

        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 将json转化为dict
        dict_data = json.loads(json_data.decode('utf8'))

        form = forms.CoursesPubForm(data=dict_data)
        if form.is_valid():
            for attr, value in form.cleaned_data.items():
                setattr(course, attr, value)

            course.save()
            return to_json_data(errmsg='课程更新成功')
        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串

            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)


class CoursesManageView(View):
    '''
    课程信息修改
    route: /admin/courses/
    '''
    def get(self, request):
        courses = Course.objects.select_related('category', 'teacher'). \
            only('title', 'category__name', 'teacher__name').filter(is_delete=False)
        return render(request, 'admin/course/course_manage.html', locals())


class CoursesPubViews(View):
    '''
    课程信息发布视图
    route: /admin/courses/pub/
    '''
    def get(self, request):
        teachers = Teacher.objects.only('name').filter(is_delete=False)
        categories = CourseCategory.objects.only('name').filter(is_delete=False)
        return render(request, 'admin/course/courses_pub.html', locals())


class GroupManageView(View):
    '''
    权限管理
    route: /admin/groups/
    '''
    def get(self, request):
        '''
        视图展示
        '''
        groups = Group.objects.values('id', 'name').annotate(num_users=Count('user')).order_by('-num_users', 'id')
        return render(request, 'admin/user/groups_manage.html', locals())


class GroupsEditView(View):
    '''
    用户组编辑
    route: /admin/groups/<int:group_id>/
    '''
    def get(self, request, group_id):
        '''
        :param group_id: 组ID
        '''
        group = Group.objects.filter(id=group_id).first()
        if group:
            permissions = Permission.objects.only('id').all()
            return render(request, 'admin/user/groups_add.html', locals())
        else:
            raise Http404('需要更新的组不存在!')

    def delete(self, request, group_id):
        '''
        删除组
        '''
        group = Group.objects.filter(id=group_id).first()
        if group:
            group.permissions.clear() # 清空权限
            group.delete()
            return to_json_data(errmsg='用户组删除成功')
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg='需要删除的用户组不存在')

    def put(self, request, group_id):
        group = Group.objects.filter(id=group_id).first()
        if not group:
            return to_json_data(errno=Code.NODATA, errmsg='需要更新的用户组不存在')

        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 将json转化为dict
        dict_data = json.loads(json_data.decode('utf8'))

        # 取出组名，进行判断
        group_name = dict_data.get('name', '').strip()
        if not group_name:
            return to_json_data(errno=Code.PARAMERR, errmsg='组名为空')

        if group_name != group.name and Group.objects.filter(name=group_name).exists():
            return to_json_data(errno=Code.DATAEXIST, errmsg='组名已存在')

        # 取出权限
        group_permissions = dict_data.get('group_permissions')
        if not group_permissions:
            return to_json_data(errno=Code.PARAMERR, errmsg='权限参数为空')

        try:
            permissions_set = set(int(i) for i in group_permissions)
        except Exception as e:
            logger.info('传的权限参数异常：\n{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='权限参数异常')

        all_permissions_set = set(i.id for i in Permission.objects.only('id'))
        if not permissions_set.issubset(all_permissions_set):
            return to_json_data(errno=Code.PARAMERR, errmsg='有不存在的权限参数')

        existed_permissions_set = set(i.id for i in group.permissions.all())
        if group_name == group.name and permissions_set == existed_permissions_set:
            return to_json_data(errno=Code.DATAEXIST, errmsg='用户组信息未修改')
        # 设置权限
        for perm_id in permissions_set:
            p = Permission.objects.get(id=perm_id)
            group.permissions.add(p)
        group.name = group_name
        group.save()
        return to_json_data(errmsg='组更新成功！')


class GroupsAddView(View):
    '''
    用户组添加
    route: /admin/groups/add/
    '''
    def get(self, request):
        permissions = Permission.objects.only('id').all()
        return render(request, 'admin/user/groups_add.html', locals())

    def post(self, request):
        '''
        处理ajax传过来的数据，创建权限组/更新权限组
        '''
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        dict_data = json.loads(json_data.decode('utf8'))

        # 取出组名，进行判断
        group_name = dict_data.get('name', '').strip()
        if not group_name:
            return to_json_data(errno=Code.PARAMERR, errmsg='组名为空')

        # 创建过is_created = False
        one_group, is_created = Group.objects.get_or_create(name=group_name)
        if not is_created:
            return to_json_data(errno=Code.DATAEXIST, errmsg='组名已存在')

        # 取出权限
        group_permissions = dict_data.get('group_permissions')
        if not group_permissions:
            return to_json_data(errno=Code.PARAMERR, errmsg='权限参数为空')

        try:
            permissions_set = set(int(i) for i in group_permissions)
        except Exception as e:
            logger.info('传的权限参数异常：\n{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='权限参数异常')

        all_permissions_set = set(i.id for i in Permission.objects.only('id'))
        # issubset: 是否包含于，True or False
        if not permissions_set.issubset(all_permissions_set):
            return to_json_data(errno=Code.PARAMERR, errmsg='有不存在的权限参数')

        # 设置权限
        for perm_id in permissions_set:
            p = Permission.objects.get(id=perm_id)
            one_group.permissions.add(p)
        one_group.save()
        return to_json_data(errmsg='组创建成功！')


class UserManageView(View):
    '''
    route: /admin/users/
    '''
    def get(self, request):
        users = Users.objects.only('username', 'is_staff', 'is_superuser').filter(is_active=True)
        return render(request, 'admin/user/user_manage.html', locals())


class UserEditView(View):
    '''
    route: /admin/users/<int:user_id>/
    '''

    def get(self, request, user_id):
        user_instance = Users.objects.filter(id=user_id).first()
        if user_instance:
            groups = Group.objects.only('name').all()
            return render(request, 'admin/user/users_edit.html', locals())
        else:
            raise Http404('需要更新的用户不存在！')

    def delete(self, request, user_id):
        user_instance = Users.objects.filter(id=user_id).first()
        if user_instance:
            user_instance.groups.clear()  # 清除用户组
            user_instance.user_permissions.clear()  # 清除用户权限
            user_instance.is_active = False  # 设置为不激活状态
            user_instance.save()
            return to_json_data(errmsg="用户删除成功")
        else:
            return to_json_data(errno=Code.PARAMERR, errmsg="需要删除的用户不存在")

    def put(self, request, user_id):
        user_instance = Users.objects.filter(id=user_id).first()
        if not user_instance:
            return to_json_data(errno=Code.NODATA, errmsg='需要更新的用户不存在')

        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 将json转化为dict
        dict_data = json.loads(json_data.decode('utf8'))

        # 取出参数，进行判断
        try:
            groups = dict_data.get('groups')  # 取出用户组列表

            is_staff = int(dict_data.get('is_staff'))
            is_superuser = int(dict_data.get('is_superuser'))
            is_active = int(dict_data.get('is_active'))
            params = (is_staff, is_superuser, is_active)
            if not all([p in (0, 1) for p in params]): # 验证爬虫信息
                return to_json_data(errno=Code.PARAMERR, errmsg='参数错误')
        except Exception as e:
            logger.info('从前端获取参数出现异常：\n{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='参数错误')

        try:
            groups_set = set(int(i) for i in groups) if groups else set()
        except Exception as e:
            logger.info('传的用户组参数异常：\n{}'.format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg='用户组参数异常')

        all_groups_set = set(i.id for i in Group.objects.only('id'))
        if not groups_set.issubset(all_groups_set):
            return to_json_data(errno=Code.PARAMERR, errmsg='有不存在的用户组参数')

        gs = Group.objects.filter(id__in=groups_set)
        # 先清除组
        user_instance.groups.clear()
        user_instance.groups.set(gs)

        user_instance.is_staff = bool(is_staff)
        user_instance.is_superuser = bool(is_superuser)
        user_instance.is_active = bool(is_active)
        user_instance.save()
        return to_json_data(errmsg='用户信息更新成功！')

















