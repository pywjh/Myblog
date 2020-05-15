# MyBlogs

#### 介绍
Django 项目 -- 博客制作

- 文章首页
  - 轮播图

  - 热文推荐

  - 文章列表

    

- 用户注册/登陆

  

- 文章详情
  - 详情内容

  - 用户评论/子评论

    

- 文章搜索

  

- 文本下载

  

- 在线视频

  - 在线视频列表页

  - 在线视频详情页

    

- 后台站点开发

  - 个人信息

  - 文章

    - 文章标签分类
    - 文章发布
    - 文章管理
    - 热门文章管理
    - 轮播图管理

  - 文档管理

  - 文档发布

  - 课程管理

  - 课程修改

  - 组管理

  - 组创建

  - 用户管理

    

#### 软件架构

- Django框架
- MySql数据库
- Redis数据库
- Docker容器
- 百度云音视频点播VOD  [百度云](https://console.bce.baidu.com/)
- AdminLTE`git clone git_ssh`下载 [AdminLTE](https://github.com/ColorlibHQ/AdminLTE)
- FastDFS
- 七牛云

#### 安装与使用教程

#####  **1. 程序包安装**

- 创建虚拟环境

  ```linux
  mkvirtualenv -p /user/bin/python3 env_name
  ```

- 所有的框架都可在虚拟环境中用pip安装

##### **2. 数据库配置**

- 完成模型的创建，迁移，生成相关的数据表
- 将datas中的数据表，以`tb_tag_20181217.sql`为首优先导入

  - ```mysql
    # 数据库导入命令，回车输入密码执行导入操作
    mysql -uusername -p -D database_name < file.sql 
    ```

  - `tb_banner....sql`

  - `tb_comments...sql`

  - `tb_docs...sql`

  - `tb_hotnews...sql`

  - `tb_news...sql`

  - `tb_tag...sql`

  - `tb_teacher.sql, tb_course.sql, tb_course_category.sql `因为涉及财产问题，需要自行设置(datas文件夹里的数据表有解释)

#####3. docker镜像相关配置

- docker通过`sudo apt-get install docker.io`安装
    - elasticsearch镜像安装：`docker image pull delron/elasticsearch-ik:2.4.6-1.0`

    - 将datas中的elasticsearch.zip文件解压

    - 通过命令运行elasticsearch容器：（最好是初始目录，不然容易出错）

      ```linux
      docker run -dti --network=host --name=elasticsearch -v 
      /home/自己的目录/elasticsearch/config:/usr/share/elasticsearch/config: delron/elasticsearch-ik:2.4.6-1.0
      ```

    - 配置好相关文件后，在虚拟环境中安装pip包

      ```linux
      # 进入项目虚拟环境
      workon virtualenv_name
      
      pip install django-haystack
      pip install elasticsearch==2.4.1
      ```

    - ```docker
      # 查看是否创建成功
      docker container ls -a 
      # 如果STATUS为Up则创建容器成功
      CONTAINER ID        IMAGE                               COMMAND                  CREATED             STATUS              PORTS               NAMES
      b254fe1ee0eb        delron/elasticsearch-ik:2.4.6-1.0   "/docker-entrypoint.…"   3 days ago          Up 3 days                               elasticsearch
      
      # 运行如下命令，如果有显示则elasticsearch配置成功
      curl 127.0.0.1:8002
      ```

    - 在settings.py文件中加入如下配置：

      ```python
      INSTALLED_APPS = [
          'haystack',
      ]
      
      ELASTICSEARCH_DSL = {
          'default': {
              'hosts': '127.0.0.1:8002'
          },
      }
      
      # Haystack
      HAYSTACK_CONNECTIONS = {
          'default': {
              'ENGINE': 'haystack.backends.elasticsearch_backend.ElasticsearchSearchEngine',
              'URL': 'http://127.0.0.1:8002/',  # 此处为elasticsearch运行的服务器ip地址，端口号默认为9200
              'INDEX_NAME': 'myblogs',  # 指定elasticsearch建立的索引库的名称
          },
      }
      
      # 设置每页显示的数据量
      HAYSTACK_SEARCH_RESULTS_PER_PAGE = 5
      # 当数据库改变时，会自动更新索引
      HAYSTACK_SIGNAL_PROCESSOR = 'haystack.signals.RealtimeSignalProcessor'
      ```

    - 配置好镜像elastisearch需要的配置后，在虚拟机中执行`pyhton manage.py rebuild_index`，生成数据库索引

    - 注意：

      - ```python
        # apps/news/search_indexes.py文件中
        # 先这样运行一次pyhton manage.py rebuild_index
        return self.get_model().objects.filter(is_delete=False, tag_id=1)
        # 再这样运行一次pyhton manage.py rebuild_index
        return self.get_model().objects.filter(is_delete=False, tag_id__in=[1, 2, 3, 4, 5, 6])
        ```

      - 

    - 用命令测试镜像是否成功运行

      ```linux
      curl 127.0.0.1:8002
      ```

      成功会显示：

      ```linux
      MyBlog$ curl 127.0.0.1:8002
      {
        "name" : "Arena",
        "cluster_name" : "elasticsearch",
        "cluster_uuid" : "NAUW08R-SEaLCbOdkCqfkQ",
        "version" : {
          "number" : "2.4.6",
          "build_hash" : "c960cd24cbdd4fe493125c0d83d76772",
          "build_timestamp" : "2017-07-18T12:17:44Z",
          "build_snapshot" : false,
          "lucene_version" : "5.5.4"
        },
        "tagline" : "You Know, for Search"
      }
      
      ```

#####4. 百度云设置

​	自行完成实名认证，成功会有55元的代金券可以使用，将自己上传的视频信息设置在程序中

视频上传成功了，单个视频右方有一个代码字段，点击可以查看视频的代码信息

- `image`就是视频的缩略图URL

- `file`就是视频的URL

- `ak`在头像的安全认证里面

  配置信息基本都在course_detail.js文件中，自行查看

```javascript
/* 在static/js/course/course_detail.js中 */


$(function () {
  let $course_data = $('.course-data');
  let sVideoUrl = $course_data.attr('data-video-url');
  let sCoverUrl = $course_data.attr('data-cover-url');

  let player = cyberplayer("course-video").setup({
    width: '100%',
    height: 650,
    file: sVideoUrl,
    image: sCoverUrl,
    autostart: false,
    stretching: "uniform",
    repeat: false,
    volume: 100,
    controls: true,
    ak: '换成百度云上面，你自己的ak'
  });

});

```

#####5. AdminLTE配置
AdminLTE是一个完善的网站后端系统界面的设计模板，整体上来说，就是将我们需要的页面设计，移植到我们自己的项目中进行在开发。

- 源文件非常大，按需所取即可。
- 创建templates/admin/base文件夹，将下载的文件夹中starter.html页面复制粘贴，放到base文件夹中，修改名字为base.html`注意模板的皮肤要与后面的标签属性相同`
- 将不需要的组件删除
- 创建static/js/admin/base文件夹、static/css/admin/base文件夹和static/css/admin/fonts文件夹，将需要的js、css、front文件从下载的源文件夹中分别复制粘贴，放到对应的项目静态文件夹内
- 创建static/images/admin/base文件夹，将用户图像文件放置其中

##### 6. 图片保存方法

1. ###### **安装FastDFS**

- 安装tracker

```docker
docker run -dti --network=host --name tracker -v /var/fdfs/tracker:/var/fdfs youkou1/fastdfs tracker
```

- 安装storage

```docker
docker run -dti --network=host --name storage -e TRACKER_SERVER=172.18.168.123:22122 -v /var/fdfs/storage:/var/fdfs youkou1/fastdfs storage
# 注意IP：172.18.168.123，要换成自己服务器的IP
```

- ***创建utils/fastdfs/logs日志文件夹，用于存放日志信息***

- utils/fastdfs/日志文件夹中的client.conf文件中

  ```python
  # the base path to store log files
  base_path=/Users/ninyoukou/PycharmProjects/dj_pre_class/utils/fastdfs/logs（自己的路径）
  #  "host:port", host can be hostname or ip address
  tracker_server=172.18.168.123:22122（自己的IP）
  ```

- 安装相关包

  ```python
  # 安装相关包
  # fdfs_client.zip文件从百度云中下载
  pip install fdfs_client.zip （存放在datas文件夹中）
  pip install mutagen
  pip install requests
  ```

2. ###### **七牛云存放图片**

- 所需模块

```pip
pip install qiniu
```

- ​	上传图片到七牛云

  - [注册](https://www.qiniu.com/)

- 实名认证成功之后，赠送10G存储空间

- 复制粘贴AK和SK

  ![copy ak sk](http://ppmnp10ew.bkt.clouddn.com/qiniu_ak_sk.jpg)

- 创建存储空间，填写空间名称，选择存储区域。访问控制选择位公开空间

  ![create storge space](http://ppmnp10ew.bkt.clouddn.com/create_store_space.jpg)



- 获取测试域名

  ![copy test domain](http://ppmnp10ew.bkt.clouddn.com/cope_test_domain.jpg)

- 创建utils/secrets/qiniu_secret_info.py文件

- ```python
  # 创建utils/secrets/qiniu_secret_info.py文件
  # 从七牛云"个人中心>密钥管理"中获取自己的 Access Key 和 Secret Key
  
  QI_NIU_ACCESS_KEY = '你自己七牛云上的AK'
  QI_NIU_SECRET_KEY = '你自己七牛云上的SK'
  QI_NIU_BUCKET_NAME = '你自己在七牛云上创建的存储空间名'
  ```

  



#### 码云特技

1. 使用 Readme\_XXX.md 来支持不同的语言，例如 Readme\_en.md, Readme\_zh.md
2. 码云官方博客 [blog.gitee.com](https://blog.gitee.com)
3. 你可以 [https://gitee.com/explore](https://gitee.com/explore) 这个地址来了解码云上的优秀开源项目
4. [GVP](https://gitee.com/gvp) 全称是码云最有价值开源项目，是码云综合评定出的优秀开源项目
5. 码云官方提供的使用手册 [https://gitee.com/help](https://gitee.com/help)
6. 码云封面人物是一档用来展示码云会员风采的栏目 [https://gitee.com/gitee-stars/](https://gitee.com/gitee-stars/)
