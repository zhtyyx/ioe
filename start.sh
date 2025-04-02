#!/bin/bash

# 设置错误时退出
set -e

# 输出环境信息
echo "当前环境变量："
echo "DJANGO_SETTINGS_MODULE: $DJANGO_SETTINGS_MODULE"
echo "DATABASE_URL: $DATABASE_URL"
echo "DJANGO_ALLOWED_HOSTS: $DJANGO_ALLOWED_HOSTS"

# 确保日志目录存在并有正确的权限
echo "设置日志目录权限..."
mkdir -p /app/logs /app/static /app/staticfiles
chmod -R 777 /app/logs

# 执行数据库迁移
echo "执行数据库迁移..."
python manage.py migrate || {
    echo "数据库迁移失败，请检查数据库连接配置"
    exit 1
}

# 收集静态文件
echo "收集静态文件..."
python manage.py collectstatic --noinput --clear || {
    echo "静态文件收集失败"
    exit 1
}

# 创建超级用户（如果不存在）
echo "检查超级用户..."
DJANGO_SUPERUSER_USERNAME=${DJANGO_SUPERUSER_USERNAME:-admin}
DJANGO_SUPERUSER_EMAIL=${DJANGO_SUPERUSER_EMAIL:-admin@example.com}
DJANGO_SUPERUSER_PASSWORD=${DJANGO_SUPERUSER_PASSWORD:-admin123}

python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
if not User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists():
    User.objects.create_superuser('$DJANGO_SUPERUSER_USERNAME', '$DJANGO_SUPERUSER_EMAIL', '$DJANGO_SUPERUSER_PASSWORD')
    print('超级用户创建成功')
else:
    print('超级用户已存在')
" || {
    echo "超级用户创建失败"
    exit 1
}

# 启动 Gunicorn
echo "启动 Gunicorn..."
exec gunicorn --bind 0.0.0.0:8000 inventory.wsgi:application --workers 4 --threads 4 --worker-class gthread --timeout 300 