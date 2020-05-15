// 将文件名设置为course_detail.js
$(function () {
  let $course_data = $('.course-data');
  let sVideoUrl = $course_data.attr('data-video-url');
  let sCoverUrl = $course_data.attr('data-cover-url');

  let player = cyberplayer("course-video").setup({ // 自动寻找id='course-video'的标签
    width: '100%', // 视频宽度
    height: 650, // 视频高度
    file: sVideoUrl, // 视频URL
    image: sCoverUrl, // 视频封面URL
    autostart: false, // 自动开始
    stretching: "uniform",
    repeat: false, // 是否循环
    volume: 60, // 音量
    controls: true, // 是否加载进度条
    ak: '使用自己百度云的ak',
  });

});
