# 使用官方 Python 3.9 镜像作为基础镜像
FROM python:3.9-slim

# 设置时区为北京时间
RUN ln -fs /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && echo 'Asia/Shanghai' > /etc/timezone

# 设置环境变量指定时区
ENV TZ=Asia/Shanghai

# 设置工作目录
WORKDIR /app

# 设置非交互式前端
env DEBIAN_FRONTEND=noninteractive

# 安装必要的系统依赖
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential \
#     && rm -rf /var/lib/apt/lists/*

# 复制 requirements.txt 文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 暴露端口 5002
EXPOSE 5002

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 启动应用
CMD ["python", "app.py"]