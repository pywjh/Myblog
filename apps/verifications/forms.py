from django import forms
from django_redis import get_redis_connection
from django.core.validators import RegexValidator

from users.models import Users

# 创建手机号的正则校验器
mobile_validator = RegexValidator(r"^1[3-9]\d{9}$", "手机号码格式不正确")


class CheckImgCodeForm(forms.Form):
    '''
    check image code
    '''
    mobile = forms.CharField(max_length=11, min_length=11, validators=[mobile_validator, ],
                             error_messages={"min_length": "手机号长度有误", "max_length": "手机号长度有误",
                                             "required": "手机号不能为空"})
    image_code_id = forms.UUIDField(error_messages={"required": "图片UUID不能为空"})
    text = forms.CharField(max_length=4, min_length=4,
                           error_messages={"min_length": "图片验证码长度有误", "max_length": "图片验证码长度有误",
                                           "required": "图片验证码不能为空"})
    # 对单字段再进行匹配使用clean_字段名
    def clean_mobile(self):
        cleaned_data = self.cleaned_data
        tel = cleaned_data.get('mobile')
        if Users.objects.filter(mobile=tel):
            raise forms.ValidationError('手机号已注册，请重新输入！')
        else:
            return tel

    def clean(self):
        cleaned_data = super().clean()

        # 1. 获取参数
        image_uuid = cleaned_data.get("image_code_id")
        image_text = cleaned_data.get("text", '') # image_text = 'abcd'
        mobile_num = cleaned_data.get("mobile")

        # 2. 建立redis链接，取出图片验证码
        # 确保settings.py文件中有配置redis CACHE
        # Redis原生指令参考 http://redisdoc.com/index.html
        # Redis python客户端 方法参考 http://redis-py.readthedocs.io/en/latest/#indices-and-tables
        con_redis = get_redis_connection(alias='verify_codes')

        # 3. 创建一把钥匙
        img_key = "img_{}".format(image_uuid).encode('utf8')

        # 4. 取出图片验证码
        real_image_code_orgin = con_redis.get(img_key)
        con_redis.delete(img_key)
        real_image_code = real_image_code_orgin.decode('utf8') if real_image_code_orgin else None

        image_text_UP = image_text.upper()

        # 5. 校验
        if (not real_image_code) or (image_text_UP != real_image_code):
            raise forms.ValidationError('图片验证码验证失败!')

        # 6. 检查是否再60s之内有发送短信验证码的记录
        sms_flag_fmt = 'sms_flag_{}'.format(mobile_num)
        sms_flag = con_redis.get(sms_flag_fmt) # 取不到值返回None
        if sms_flag:
            raise forms.ValidationError('获取短信验证码频繁')

















