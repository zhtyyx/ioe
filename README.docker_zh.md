# Docker 部署指南

[English](README.docker_en.md) · [返回项目说明](README_zh.md)

仓库提供 `docker-compose.yml` 和 `docker-compose.prod.yml`。两者都运行同一个 Django 容器，默认使用 SQLite；`prod` 文件主要把 `DEBUG` 默认值设为 `False`，不是一套完整的生产环境方案。

## 准备

需要安装 Docker 和 Docker Compose 插件（命令为 `docker compose`）。在仓库根目录执行：

```bash
git clone https://github.com/zhtyyx/ioe.git
cd ioe
cp .env.template .env
python3 -c 'import secrets; print(secrets.token_urlsafe(50))'
```

把最后一条命令生成的随机值填入 `.env` 的 `SECRET_KEY`。不要沿用模板中的占位值，也不要提交 `.env`。把 `ALLOWED_HOSTS` 改为实际访问的域名或地址，多个值用逗号分隔。本地调试可将 `DEBUG` 改为 `True`；对外部署保持 `False`。

目前 Compose 只向 Django 传入 `DEBUG`、`SECRET_KEY` 和 `ALLOWED_HOSTS`。数据库固定为 SQLite，`.env` 中的其他配置不会自动切换数据库或邮件服务。

## 启动

本地运行：

```bash
docker compose up -d --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py collectstatic --noinput
docker compose exec web python manage.py createsuperuser
```

打开 <http://localhost:8000/> 并登录。`createsuperuser` 只需为新环境执行一次；以后更新代码或首次挂载新数据卷时，应重新运行 `migrate`。Dockerfile 虽在镜像构建时运行迁移和静态文件收集，运行中的数据库和静态目录使用挂载卷，因此仍需执行上面的运行时命令。

如果要使用生产配置示例，把上述命令中的 `docker compose` 全部替换为 `docker compose -f docker-compose.prod.yml`，并在启动前确认 `.env` 中 `DEBUG=False`、`ALLOWED_HOSTS` 和随机 `SECRET_KEY`。该配置仍直接暴露 8000 端口、挂载仓库目录，缺少 HTTPS 反向代理等生产防护；不能仅凭文件名把它当作已经加固的公网部署。

## 数据与运维

| 位置 | 内容 |
| --- | --- |
| `db_volume` | SQLite 数据库，容器内路径 `/app/db` |
| `media_volume` | 上传的图片，容器内路径 `/app/media` |
| `static_volume` | 收集后的静态资源，容器内路径 `/app/staticfiles` |
| 仓库中的 `logs/` | 运行日志，通过绑定挂载写回宿主机 |

常用命令：

```bash
docker compose logs -f web
docker compose exec web python manage.py check
docker compose down
```

`docker compose down` 不会删除上述命名卷；不要在需要保留数据时使用 `down -v`。备份时同时保存数据库卷和媒体卷。若使用生产配置示例，常用命令也要加 `-f docker-compose.prod.yml`。

镜像构建期间，Dockerfile 已为 apt 和 pip 配置清华镜像源；它们只影响镜像构建时的依赖下载。
