import yagmail

from .email_info import username, password

def to_eamil_message(token, mobile):
    try:
        # 链接邮箱服务器
        yag = yagmail.SMTP(user=username, password=password, host='smtp.163.com', port='465')
        # 邮箱正文
        contents = ['\t你好，欢迎来到pywjh的博客，由于短信业务收费，所以选择了邮箱操作（多low啊）\n\t哈哈哈，你的邮箱验证码为：{}'.format(token)]

        # recipients = {
        #     '1243781831@qq.com': '老婆',
        #     '1376828025@qq.com': '我自己',
        # }

        # 发送邮件
        yag.send(
            # to=recipients,
                 to=mobile,
                 subject='注册信息验证',
                 contents=contents)
        return '邮箱发送成功'
    except Exception:
        return '邮件发送失败'