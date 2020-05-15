import logging
import json
import random
import string

from django.views import View
from django_redis import get_redis_connection
from django.http import HttpResponse

from utils.captcha.captcha import captcha
from utils.json_fun import to_json_data
from utils.res_code import Code, error_map
from . import constants
from users.models import Users
from .forms import CheckImgCodeForm
from .to_email import to_eamil_message
# from utils.yuntongxun.sms import CCP

# 导入日志器
logger = logging.getLogger('django')


class ImageCode(View):
    """
    define image verification view
    # /image_codes/<uuid:image_code_id>/
    """

    def get(self, request, image_code_id):
        # 通过项目中自带的captcha.py生成验证码文本和图片
        text, image = captcha.generate_captcha()
        '''
        # 确保settings.py文件中有配置redis CACHE
        # Redis原生指令参考 http://redisdoc.com/index.html
        # Redis python客户端 方法参考 http://redis-py.readthedocs.io/en/latest/#indices-and-tables
        '''
        # 连接redis数据库
        con_redis = get_redis_connection(alias='verify_codes')
        # 创建一个验证码的钥匙，形如"img_uuid码"
        img_key = "img_{}".format(image_code_id).encode('utf-8')
        # 将图片验证码的key和验证码文本保存到redis中，并设置过期时间
        con_redis.setex(img_key, constants.IMAGE_CODE_REDIS_EXPIRES, text)
        logger.info("Image code: {}".format(text))
        # 将验证码二进制格式传给前端并设置文本类型
        return HttpResponse(content=image, content_type="image/jpg")


class CheckUsernameView(View):
    """
    check whether the user exists
    method: auth.js ajax GET
    route: usernames/(?P<username>\w{5,20})/
    :return auth.js ajax验证
    # 1、创建一个类视图
    """

    # 2、校验参数
    def get(self, request, username):
        # 3、查询数据
        count = Users.objects.filter(username=username).count()
        # try:
        #     user = Users.objects.get(username=username)
        # except  DoesNotExist:
        #     return to_json_data(errno=Code.NODATA, errmsg=error_map[Code.NODATA])
        data = {
            'username': username,
            'count': count
        }
        # return JsonResponse(data=data)
        return to_json_data(data=data)


class CheckMobileView(View):
    '''
    check mobile whatever exists
    GET: mobiles/(?P<mobile>1[3-9]\d{9})/
    '''
    # 1. 定义类似图
    # 校验数据
    def get(self, request, mobile):
        # 2. 查询数据
        count = Users.objects.filter(mobile=mobile).count()
        data = {
            'mobile': mobile,
            'count': count
        }
        return to_json_data(data=data)


class SmsCodeView(View):
    '''
    send mobile sms code
    POST /sms_code/
    # 1. 创建类视图
    '''
    def post(self, request):
        # 2. 获取前端传过来的json格式数据 形如：b'{"mobile":"17666667779","text":"UW47","image_code_id":"f56f3f3d-08db-48e6-a14c-5d55fbd39eb5"}'
        json_data = request.body # b'{\n\t"mobile": "111"\n....}'
        if not json_data:
            return to_json_data(errno=Code.PARAMERR, errmsg=error_map[Code.PARAMERR])
        # 讲前端传回来的数据编码再转化为字典
        dict_data = json.loads(json_data.decode('utf-8'))
        # 3. 校验数据
        # mobile = dict_data.get('mobile')
        # image_code_id = dict_data.get('image_code_id')
        # text = dict_data.get('text')
        form = CheckImgCodeForm(data=dict_data)
        if form.is_valid():
            # 4. 发送短信验证码
            # 获取手机号
            mobile = form.cleaned_data.get('mobile')
            # 生成短信验证码
            sms_num = ''.join([random.choice(string.digits) for _ in range(6)])
            redis_conn = get_redis_connection(alias='verify_codes')
            p1 = redis_conn.pipeline()
            sms_flag_fmt = 'sms_flag_{}'.format(mobile)
            sms_text_fmt = 'sms_{}'.format(mobile)
            # redis_conn.setex(sms_flag_fmt, 60, 1)
            # redis_conn.setex(sms_text_fmt, 300, sms_num)
            try:
                # 5. 将短信验证码文本和发送短信验证码记录保存在redis中
                # 设置通道 符
                p1.setex(sms_flag_fmt, constants.SEND_SMS_CODE_INTERVAL, 1)
                p1.setex(sms_text_fmt, constants.SMS_CODE_REDIS_EXPIRES, sms_num)
                # 开启通道服务
                p1.execute()
            except Exception as e:
                logger.debug('redis执行出现异常：{}'.format(e))
                # 6. 将json格式数据返回给前端
                return to_json_data(errno=Code.UNKOWNERR, errmsg=error_map[Code.UNKOWNERR])

            logger.info("发送验证码短信[正常][mobile:%s sms_code:%s]"%(mobile, sms_num))

            result = to_eamil_message(sms_num, mobile)

            return to_json_data(errmsg="短信验证码发送成功")


            # 为了开发测试，这里不使用短信功能板块
            # try:
            #     result = CCP().send_template_sms(mobile, [sms_num, constants.SMS_CODE_YUNTX_EXPIRES],
            #                                      constants.SMS_CODE_TEMP_ID)
            # except Exception as e:
            #     logger.error("发送验证码短信[异常][ mobile: %s, message: %s ]" % (mobile, e))
            #     return to_json_data(errno=Code.SMSERROR, errmsg=error_map[Code.SMSERROR])
            # else:
            #     if result == 0:
            #         logger.info("发送验证码短信[正常][ mobile: %s sms_code: %s]" % (mobile, sms_num))
            #         return to_json_data(errno=Code.OK, errmsg="短信验证码发送成功")
            #     else:
            #         logger.warning("发送验证码短信[失败][ mobile: %s ]" % mobile)
            #         return to_json_data(errno=Code.SMSFAIL, errmsg=error_map[Code.SMSFAIL])


        else:
            # 定义一个错误信息列表
            err_msg_list = []
            for item in form.errors.get_json_data().values():
                err_msg_list.append(item[0].get('message'))
                # print(item[0].get('message'))   # for test
            err_msg_str = '/'.join(err_msg_list)  # 拼接错误信息为一个字符串

            return to_json_data(errno=Code.PARAMERR, errmsg=err_msg_str)





