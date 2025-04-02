# 使用 Python 3.11 作为基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV TZ=Asia/Shanghai

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    postgresql-client \
    netcat-traditional \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 创建必要的目录
RUN mkdir -p /app/media /app/backups /app/temp /app/logs /app/static /app/staticfiles && \
    chmod -R 777 /app/logs

# 复制项目文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir whitenoise \
    && rm -rf /root/.cache/pip/*

# 复制项目文件
COPY . .

# 收集静态文件
RUN python manage.py collectstatic --noinput

# 设置启动脚本权限
RUN chmod +x /app/start.sh

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["/app/start.sh"] 