import json
import logging

from django.shortcuts import render
from django.views import View
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponseNotFound
from haystack.views import SearchView as _SearchView
from django.conf import settings

from . import models
from . import contants
from utils.json_fun import to_json_data
from utils.res_code import Code, error_map


logger = logging.getLogger('django')


class IndexView(View):
    '''
    handle index
    route: no url path
    '''

    def get(self, request):
        '''get请求，返回首页'''
        tags = models.Tag.objects.only('id', 'name').filter(is_delete=False)
        hot_news = models.HotNews.objects.select_related('news').only('news__title', 'news__image_url', 'news_id').filter(is_delete=False).order_by('priority', '-news__clicks')[:contants.SHOW_HOT_NEWS_COUNT]
        return render(request, 'news/index.html', locals())


# 1. 创建一个类视图
# 2. 获取前端传过来的参数
# 3. 校验参数
# 4. 从数据库中获取news数据
# 5. 分页展示内容
# 6. 返回json格式的数据
class NewsListView(View):
    '''
    create news list view
    route: /news/
    // 127.0.0.1:8000/news?tag_id=1&page=1
    '''
    def get(self, request):
        try:
            # 获取前端点击返回的tag， 错误请求直接返回0（最新资讯）
            tag_id = int(request.GET.get('tag_id', 0))
        except Exception as e:
            logger.error("标签错误: \n{}".format(e))
            tag_id = 0

        try:
            # 获取前端返回的页数请求，错误请求直接返回第一页
            page = int(request.GET.get('page', 1))
        except Exception as e:
            logger.error('当前页错误: \n{}'.format(e))
            page = 1

        # 关联查询数据，only过滤数据
        news_queryset = models.News.objects.select_related('tag', 'author').\
            only('title', 'digest', 'image_url', 'update_time', 'tag__name', 'author__username')
        # 从数据库中取出数据，操作有误就直接返回全部数据
        news = news_queryset.filter(is_delete=False, tag_id=tag_id) or news_queryset.filter(is_delete=False)

        paginator = Paginator(news, contants.PER_PAGE_NEWS_COUNT)
        try:
            news_info = paginator.page(page)
        except PageNotAnInteger:
            logging.info("用户请求非整形页")
            news_info = paginator.page(1)
        except EmptyPage:
            # 若用户访问的页数大于实际页数，则返回最后一页数据
            logging.info("用户访问的页数大于总页数。")
            news_info = paginator.page(paginator.num_pages)

        # 序列化输出
        news_info_list = []
        for i in news_info:
            news_info_list.append({
                'id': i.id,
                'title': i.title,
                'digest': i.digest,
                'image_url': i.image_url,
                'tag_name': i.tag.name,
                'author': i.author.username,
                'update_time': i.update_time.strftime('%Y年%m月%d日 %H:%M'),
            })
        # 创建返回前端的数据
        data = {
            'total_pages': paginator.num_pages,
            'news': news_info_list
        }

        return to_json_data(data=data)


class NewsBannerView(View):
    '''
    news banner view
    route: news/banners/
    '''
    def get(self, request):
        banners = models.Banner.objects.select_related('news').only('image_url', 'news_id', 'news__title').filter(is_delete=False)[:contants.SHOW_BANNER_COUNT]

        banners_info_list = []
        for b in banners:
            banners_info_list.append({
                'image_url': b.image_url,
                'news_id': b.news.id,
                'news_title': b.news.title
            })
        data = {
            'banners': banners_info_list
        }
        return to_json_data(data=data)


class NewsDetailView(View):
    '''handle news_detail'''

    def get(self, request, news_id):
        '''get请求，返回详情页'''
        news = models.News.objects.select_related('tag', 'author').only('title', 'content', 'update_time', 'tag__name', 'author__username').filter(is_delete=False, id=news_id).first()
        if news:
            comments = models.Comment.objects.select_related('author', 'parent').only('content', 'author__username', 'update_time','parent__author__username', 'parent__content', 'parent__update_time').filter(is_delete=False, news_id=news_id)
            # 序列化输出
            comments_list = []
            for comm in comments:
                comments_list.append(comm.to_dict_data())

            comment_num = len(comments_list)

            return render(request, 'news/news_detail.html', locals())
        else:
            return HttpResponseNotFound('<h1>Page not found!</h1>')


class NewsCommentView(View):
    '''
    create news's comments
    route: /news/<int:news_id>/comment/
    '''
    def post(self, request, news_id):
        if not request.user.is_authenticated: # 如果用户没有登陆，不允许添加自评论
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.SESSIONERR])

        if not models.News.objects.only('id').filter(is_delete=False, id=news_id).exists():
            return to_json_data(errno=Code.PARAMERR, errmsg='文章不存在')

        # 从前端获取参数
        json_data = request.body
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.UNKOWNERR])
        dict_data = json.loads(json_data.decode('utf-8'))

        content = dict_data.get('content')
        # 获取用户评论
        if not content:
            return to_json_data(errno=Code.PARAMERR, errmsg='评论不能为空')
        parent_id = dict_data.get('parent_id')
        try:
            if parent_id:
                parent_id = int(parent_id)
                if not models.Comment.objects.only('id'). \
                    filter(is_delete=False, id=parent_id,
                           news_id=news_id).exists():
                    return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])

        except Exception as e:
            logging.info("前端传过来的parent_id异常：\n{}".format(e))
            return to_json_data(errno=Code.PARAMERR, errmsg="未知异常")

            # 保存到数据库
        new_content = models.Comment()
        new_content.content = content
        new_content.news_id = news_id
        new_content.author = request.user
        new_content.parent_id = parent_id if parent_id else None
        new_content.save()

        return to_json_data(data=new_content.to_dict_data())


class SearchView(_SearchView):
    # 模版文件
    template = 'news/search.html'

    # 重写响应方式，如果请求参数q为空，返回模型News的热门新闻数据，否则根据参数q搜索相关数据
    def create_response(self):
        kw = self.request.GET.get('q', '')
        if not kw:
            show_all = True
            hot_news = models.HotNews.objects.select_related('news'). \
                only('news__title', 'news__image_url', 'news__id'). \
                filter(is_delete=False).order_by('priority', '-news__clicks')

            paginator = Paginator(hot_news, settings.HAYSTACK_SEARCH_RESULTS_PER_PAGE)
            try:
                page = paginator.page(int(self.request.GET.get('page', 1)))
            except PageNotAnInteger:
                # 如果参数page的数据类型不是整型，则返回第一页数据
                page = paginator.page(1)
            except EmptyPage:
                # 用户访问的页数大于实际页数，则返回最后一页的数据
                page = paginator.page(paginator.num_pages)
            return render(self.request, self.template, locals())
        else:
            show_all = False
            qs = super(SearchView, self).create_response()
            return qs

