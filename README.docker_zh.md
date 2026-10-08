# Docker 镜像部署

[English](README.docker_en.md) · [返回项目说明](README_zh.md) · [构建状态](https://github.com/zhtyyx/ioe/actions/workflows/publish-image.yml)

使用 `ghcr.io/zhtyyx/ioe:latest`，无需克隆代码或在服务器上构建镜像。支持 Linux AMD64 和 ARM64。需要 Docker，以及 **Docker Compose 2.23.1 或更新版本**。

## 1. 下载部署配置

在一个新的部署目录中执行：

```bash
mkdir -p ioe
cd ioe
curl -fsSL https://raw.githubusercontent.com/zhtyyx/ioe/main/docker-compose.prod.yml -o compose.yaml
curl -fsSL https://raw.githubusercontent.com/zhtyyx/ioe/main/.env.template -o .env
openssl rand -hex 32
```

把生成的随机值填入 `.env` 的 `SECRET_KEY`，把 `ALLOWED_HOSTS` 改为实际使用的域名或服务器 IP。保留 `localhost,127.0.0.1` 可同时从本机访问；多个值用逗号分隔，不带协议或端口。不要公开 `.env`，更新时也不要覆盖它。

例如：

```dotenv
SECRET_KEY=替换为刚生成的随机值
ALLOWED_HOSTS=localhost,127.0.0.1,你的服务器IP
IOE_PORT=8000
```

## 2. 拉取并启动

```bash
docker compose pull
docker compose up -d --wait
docker compose exec web python manage.py createsuperuser
```

打开 `http://服务器IP:8000/`，使用刚创建的管理员账号登录。首次启动为空数据库；容器启动时自动执行数据库迁移并收集静态资源，管理员账号由你手动创建一次。

部署包含两个服务：`web` 运行 Django / Gunicorn，`nginx` 提供页面入口、静态资源和上传图片。生产配置固定 `DEBUG=False`，不挂载本地源码。对公网提供服务时，在入口配置域名和 HTTPS。

修改端口可以在 `.env` 中设置 `IOE_PORT=8080`。若只供本机反向代理访问，可设置 `IOE_BIND_ADDRESS=127.0.0.1`。

## 3. 更新镜像

先备份数据库和上传文件，再执行：

```bash
docker compose pull
docker compose up -d --force-recreate --wait
docker compose logs --tail=100 web
```

更新会使用原有数据卷，并执行新版数据库迁移。保留原部署目录和 Compose 项目名，不要换到另一个目录后误以为旧数据丢失。`--force-recreate` 会同时刷新应用与代理容器。

### 镜像标签

| 标签 | 用途 |
| --- | --- |
| `latest` | `main` 分支最近一次通过测试并发布的版本 |
| `sha-<完整提交 SHA>` | 固定某次代码提交的构建 |
| `1.2.3` / `1.2` | 推送 `v1.2.3` 这类版本标签时生成；仅发布过的标签可用 |

在 `.env` 设置 `IOE_IMAGE=ghcr.io/zhtyyx/ioe:sha-<完整提交 SHA>` 可固定版本。镜像也可以按 `@sha256:...` 摘要固定。旧镜像不一定兼容已经升级的数据库；需要回滚时，应使用对应版本的数据库备份。

## 数据保存位置

| 命名卷 | 容器路径与内容 |
| --- | --- |
| `db_volume` | `/app/db`：SQLite 数据库 |
| `media_volume` | `/app/media`：上传图片 |
| `backups_volume` | `/app/backups`：系统内创建的备份 |
| `logs_volume` | `/app/logs`：应用日志 |
| `static_volume` | `/app/staticfiles`：启动时收集的静态资源 |

```bash
docker compose logs -f web
docker compose exec web python manage.py check
docker compose down
```

`down` 保留命名卷；`down -v` 会删除这些卷及其数据。不要用后者更新应用。

已有源码部署迁移到镜像部署时，先备份并确认原来的 Compose 项目名和卷名。新版沿用 `db_volume`、`media_volume` 和 `static_volume` 这三个卷的逻辑名称；原先保存在宿主机 `logs/`、`backups/` 的内容不会自动复制进新卷。不要直接在真实业务库上试迁移。

## GitHub Actions 发布机制

[Publish container image](.github/workflows/publish-image.yml) 在推送 `main`、推送 `v*` 标签或手动触发时运行：

1. 构建测试镜像，运行 Django 测试。
2. 验证空库启动、登录页面、静态资源、上传文件及容器重建后的持久化。
3. 使用仓库自带的 `GITHUB_TOKEN` 发布 AMD64 / ARM64 镜像到 GHCR。

PR 只构建和测试，不登录 GHCR、不推送镜像。无需配置 Docker Hub 账号或个人访问令牌。

**首次发布的可见性：** GHCR 新包默认是私有的。仓库维护者需要在 [IOE 镜像设置](https://github.com/users/zhtyyx/packages/container/ioe/settings) 中将可见性设为 Public，之后用户即可匿名拉取。首次使用前确认 Actions 已成功发布；若出现 `denied`，检查包的可见性，若出现 `manifest unknown`，检查所用标签是否已发布。[GitHub 官方说明](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)

## 从源码构建（开发用）

需要修改代码时，先自行构建镜像，再用相同的部署配置启动：

```bash
git clone https://github.com/zhtyyx/ioe.git
cd ioe
cp .env.template .env
# 按前文填写 SECRET_KEY 和 ALLOWED_HOSTS，再执行：
docker build -t ioe:local .
IOE_IMAGE=ioe:local docker compose -f docker-compose.prod.yml up -d --wait
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

该方式把修改后的代码打包进镜像，不挂载本地源码。需要验证部署配置时，可运行：

```bash
docker build -t ioe:local .
sh scripts/test-container.sh ioe:local
```

验证脚本使用独立的临时项目和数据卷，完成后只清理它自己创建的容器与卷。
