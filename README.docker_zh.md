# Docker部署指南

本文档提供了使用Docker部署本应用的详细说明。

## 前提条件

- 安装 [Docker](https://docs.docker.com/get-docker/)
- 安装 [Docker Compose](https://docs.docker.com/compose/install/)

## 开发环境部署

1. 克隆代码库

```bash
git clone <repository-url>
cd ioe
```

2. 创建环境变量文件

```bash
cp .env.example .env
# 编辑.env文件，填入正确的配置信息
```

3. 构建并启动容器

```bash
docker-compose up --build
```

4. 访问应用

打开浏览器，访问 http://localhost:8000

## 生产环境部署

1. 克隆代码库

```bash
git clone <repository-url>
cd ioe
```

2. 创建环境变量文件

```bash
cp .env.template .env
# 编辑.env文件，填入正确的配置信息，特别是SECRET_KEY和ALLOWED_HOSTS
```

3. 使用生产配置启动容器

```bash
docker-compose -f docker-compose.prod.yml up -d
```

4. 创建超级用户（如果需要）

```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

## 数据持久化

在生产环境中，数据存储在Docker卷中：

- `static_volume`: 静态文件
- `media_volume`: 媒体文件（如上传的图片）
- `db_volume`: 数据库文件

## 常用命令

- 查看日志：`docker-compose logs -f`
- 停止服务：`docker-compose down`
- 重启服务：`docker-compose restart`
- 执行Django管理命令：`docker-compose exec web python manage.py <command>`

## 自定义配置

如需自定义Docker配置，可以编辑以下文件：

- `Dockerfile`: 修改应用环境
- `docker-compose.yml`: 修改开发环境服务配置
- `docker-compose.prod.yml`: 修改生产环境服务配置

## 注意事项

1. 生产环境中，请确保设置了安全的SECRET_KEY
2. 更新ALLOWED_HOSTS以包含您的域名
3. 考虑使用外部数据库服务（如PostgreSQL）替代SQLite以获得更好的性能
4. 定期备份数据卷中的数据