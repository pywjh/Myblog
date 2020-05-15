import logging

from django.shortcuts import render
from django.views import View
from django.http import Http404

from . import models

logger = logging.getLogger('django')


def course_list(request):
    course = models.Course.objects.only('title', 'cover_url', 'teacher__positional_title').filter(is_delete=False)
    return render(request, 'course/course(1).html', locals())


class CourseDetailViews(View):
    '''handle course_detail'''

    def get(self, request, course_id):
        '''get请求，返回课程详情页面'''
        try:
            course = models.Course.objects.only('title', 'cover_url', 'video_url', 'profile', 'outline', 'teacher__name', 'teacher__avatar_url', 'teacher__positional_title', 'teacher__profile').select_related('teacher').filter(is_delete=False, id=course_id).first()
            return render(request, 'course/course_detail.html', locals())
        except models.Course.DoesNotExist as e:
            logger.info('当前课程出现如下异常：\n{}'.format(e))
            raise Http404('<h1>此课程不存在！</h1>')
