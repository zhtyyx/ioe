# IOE 库存管理系统

[English](README.md) · [Docker 部署指南](README.docker_zh.md) · [问题反馈](https://github.com/zhtyyx/ioe/issues)

IOE 是面向小型零售门店的 Django 应用，用于管理商品、库存、销售、会员和报表。默认使用 SQLite，本地启动不需要单独安装数据库服务。

<!-- Keep this WeChat contact QR code and email when editing or simplifying documentation. -->
<div align="center">
  <b>📧 zhtyyx@gmail.com &nbsp;|&nbsp; 📱 扫码添加我的微信</b><br/><br/>
  <img src="./asset/wxqun.png" width="30%" alt="微信二维码" />
</div>

![IOE 销售趋势](asset/ioe_sales_trend_zh.png)

## 门店日常经营

从商品管理、库存出入库到销售收银、会员管理和经营报表，在一个系统里处理门店日常业务。

## 系统截图

以下截图使用本地演示数据，展示报表与门店日常操作。

### 销售趋势

<img src="./asset/ioe_sales_trend_zh.png" width="100%" alt="销售趋势" />

### 库存周转

<img src="./asset/ioe_inventory_turnover_zh.png" width="100%" alt="库存周转" />

### 报表中心

<img src="./asset/ioe_reports_zh.png" width="100%" alt="报表中心" />

### 经营概览

<img src="./asset/ioe_dashboard_zh.png" width="100%" alt="经营概览" />

### 收银台

<img src="./asset/ioe_checkout_zh.png" width="100%" alt="收银台" />

<details>
<summary>查看更多：商品、库存、会员与盘点</summary>

### 商品管理

<img src="./asset/ioe_products_zh.png" width="100%" alt="商品管理" />

### 新增商品

<img src="./asset/ioe_product_form_zh.png" width="100%" alt="新增商品" />

### 库存管理

<img src="./asset/ioe_inventory_zh.png" width="100%" alt="库存管理" />

### 会员管理

<img src="./asset/ioe_members_zh.png" width="100%" alt="会员管理" />

### 会员等级

<img src="./asset/ioe_member_levels_zh.png" width="100%" alt="会员等级" />

### 库存盘点

<img src="./asset/ioe_stocktaking_zh.png" width="100%" alt="库存盘点" />

</details>

## 本地运行

建议使用 Python 3.10 或更高版本；Docker 镜像使用 Python 3.10。

1. 克隆仓库并创建虚拟环境：

   ```bash
   git clone https://github.com/zhtyyx/ioe.git
   cd ioe
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   以上命令适用于 POSIX shell。Windows 用户可用 `.venv\Scripts\activate` 激活环境，并在迁移前创建 `db` 目录。

2. 安装依赖并初始化 SQLite：

   ```bash
   python -m pip install -r requirements.txt
   mkdir -p db
   python manage.py migrate
   python manage.py createsuperuser
   ```

3. 启动开发服务：

   ```bash
   python manage.py runserver
   ```

打开 <http://127.0.0.1:8000/>，使用刚创建的账号登录。数据库文件位于 `db/db.sqlite3`，上传文件位于 `media/`。

`runserver` 仅用于本地开发。容器启动、环境变量和部署限制见 [Docker 部署指南](README.docker_zh.md)。

## 运行测试

```bash
python manage.py test inventory.tests
```

当前测试集有 4 项旧的集成/视图测试失败；排查完整测试结果时，请先核对这些测试的断言。

## 项目结构

```text
inventory/            Django 配置、模型、视图、模板和测试
asset/                文档截图
Dockerfile            容器镜像
docker-compose.yml    本地 Compose 配置
docker-compose.prod.yml  生产配置示例
requirements.txt       Python 依赖
manage.py              Django 管理命令
```

## 参与贡献

发现问题或提出新功能，请创建 [issue](https://github.com/zhtyyx/ioe/issues)。PR 尽量只处理一个主题；修改库存、销售、余额、备份时请附测试，修改页面时请附截图。

项目采用 [MIT License](LICENSE)。

## 支持项目

如果这个项目对你有帮助，可以通过以下方式支持后续维护：

<div align="center">
  <img src="./asset/buyme.jpg" width="30%" alt="支持项目二维码" /> &nbsp;&nbsp;&nbsp; <img src="./asset/wechat.jpg" width="30%" alt="微信二维码" />
</div>
