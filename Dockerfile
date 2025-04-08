FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建数据库目录
RUN mkdir -p /app/db

# 设置 /app 目录及其内容的权限为 777 (临时调试)
RUN chmod -R 777 /app

# 创建日志目录并设置权限
RUN mkdir -p logs && chmod 777 logs

# 收集静态文件
RUN python manage.py collectstatic --noinput

# 自动执行数据库迁移和创建超级用户
RUN python manage.py migrate
# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["gunicorn", "inventory.wsgi:application", "--bind", "0.0.0.0:8000"]