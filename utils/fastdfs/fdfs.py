#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from fdfs_client.client import Fdfs_client

# 指定fdfs客户端配置文件所在路径
FDFS_Client = Fdfs_client(r'utils/fastdfs/client.conf')

# if __name__ == '__main__':
#     try:
#         ret = FDFS_Client.upload_by_filename('media/linux.jpg')
#     except Exception as e:
#         print("fdfs测试异常：{}".format(e))
#     else:
#         print(ret)
