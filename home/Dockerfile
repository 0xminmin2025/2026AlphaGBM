# 使用Nginx作为基础镜像
FROM nginx:alpine

# 移除默认的Nginx欢迎页面
RUN rm -rf /usr/share/nginx/html/*

# 将home目录下的所有内容复制到Nginx的静态文件目录
COPY ./index.html /usr/share/nginx/html/
COPY ./WeChat-QR-Code.jpg /usr/share/nginx/html/


# 设置正确的文件权限
RUN chmod -R 755 /usr/share/nginx/html/

# 暴露80端口
EXPOSE 80

# 启动Nginx服务器
CMD ["nginx", "-g", "daemon off;"]