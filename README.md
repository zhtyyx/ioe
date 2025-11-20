<div align="center">

# 📦 IOE 库存管理系统 | Inventory Management System

[![Django](https://img.shields.io/badge/Django-3.2+-green.svg)](https://www.djangoproject.com/) &nbsp; [![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/) &nbsp; [![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) &nbsp; [![Docker](https://img.shields.io/badge/Docker-Ready-brightgreen.svg)](README.docker.md)

_一站式零售库存解决方案，为您的商店量身定制_

<p align="center">
  <a href="README_zh.md">中文</a> | <a href="README_en.md">English</a>
</p>

</div>

## 🚀 项目概述

IOE是一个基于Django开发的**综合性库存管理系统**，专为零售商店、小型仓库和商品销售场所设计。系统提供了完整的商品管理、库存跟踪、销售记录、会员管理和数据分析功能，帮助企业高效管理库存和销售流程。

<div align="center">
  <b>📱 扫描二维码添加我的微信，加入分享群，获取技术支持与分享经验</b><br/><br/>
  <img src="./asset/wxqun.png" width="30%" />
</div>

## ✨ 主要功能模块

### 🏷️ 商品管理

- **商品信息管理**：添加、编辑和查看商品详细信息，包括名称、条码、价格等
- **商品分类管理**：创建和管理商品分类，便于组织和查询
- **商品规格管理**：设置商品的颜色、尺码、规格和制造商等属性
- **商品图片上传**：上传和管理商品图片

### 📊 库存管理

- **实时库存跟踪**：精确掌握每个商品的库存数量
- **智能库存预警**：设置阈值，低库存自动提醒
- **入库/出库管理**：系统自动更新库存数量
- **库存调整**：支持手动调整和批量操作
- **全面交易记录**：详细记录所有库存变动明细

### 📝 库存盘点

- **盘点计划创建**：周期性或临时库存盘点安排
- **高效盘点执行**：记录实际与系统差异
- **盘点审核流程**：确保盘点数据准确性
- **详细盘点报告**：生成可视化盘点差异报告
- **自动库存调整**：根据盘点结果一键调整

### 💰 销售管理

- **销售单创建**：直观便捷的销售操作界面
- **多元支付方式**：现金、微信、支付宝、银行卡和账户余额等
- **灵活销售折扣**：支持多种折扣策略
- **销售记录查询**：多维度筛选历史销售数据
- **无忧退货处理**：简化销售退货流程

### 👥 会员管理

- **会员信息管理**：全面记录会员基础资料
- **会员等级体系**：自定义等级和专属优惠
- **积分奖励系统**：消费自动累积积分
- **消费历史追踪**：会员消费行为分析
- **账户余额管理**：充值与消费一体化
- **贴心生日提醒**：增强会员关怀

### 📊 数据分析与报表

- **销售趋势图表**：直观展示业务走向
- **商品表现分析**：识别热销与滞销商品
- **库存健康评估**：优化库存投资回报
- **利润精准计算**：多维度利润分析
- **会员价值评估**：深入了解会员贡献
- **系统使用审计**：全面操作日志记录

## 💡 系统特点

| 特点 | 描述 |
|------|------|
| 📱 用户友好 | 简洁直观的界面设计，易于上手和使用 |
| 🔄 功能完善 | 覆盖零售业务全流程，从商品入库到销售、会员管理 |
| 📊 数据可视化 | 丰富的报表和图表，直观展示业务数据 |
| 🔒 安全可靠 | 完善的权限控制和操作日志，保障数据安全 |
| 🔌 灵活扩展 | 模块化设计，易于扩展新功能 |
| 👥 社区支持 | 活跃的用户交流群，分享经验和解决问题 |

## 🚀 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 数据库配置与初始化

```bash
# 1. 创建数据库（以MySQL为例）
CREATE DATABASE ioe CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 2. 修改项目配置文件中的数据库设置（project/settings.py）

# 3. 执行数据库迁移
python manage.py migrate
```

### 创建管理员账户

```bash
python manage.py createsuperuser
```

### 启动服务

```bash
python manage.py runserver
```

### 访问系统

在浏览器中访问 [http://127.0.0.1:8000/](http://127.0.0.1:8000/) 即可使用系统

### Docker部署

对于生产环境，推荐使用Docker部署，详细说明请参阅[Docker部署指南](README.docker.md)

## 📸 系统截图

<div align="center">
  <img src="./asset/开始盘点.png" width="100%" /><br/><br/>
  <img src="./asset/报表中心.png" width="100%" /><br/><br/>
  <img src="./asset/会员等级管理.png" width="100%" /><br/><br/>
  <img src="./asset/会员管理.png" width="100%" /><br/><br/>
  <img src="./asset/商品分类列表.png" width="100%" /><br/><br/>
  <img src="./asset/导入会员.png" width="100%" /><br/><br/>
  <img src="./asset/库存列表.png" width="100%" /><br/><br/>
  <img src="./asset/库存盘点.png" width="100%" /><br/><br/>
  <img src="./asset/收银台-添加商品.png" width="100%" /><br/><br/>
  <img src="./asset/添加会员.png" width="100%" /><br/><br/>
  <img src="./asset/销售记录.png" width="100%" /><br/><br/>
  <img src="./asset/main_page.png" width="100%" /><br/><br/>
</div>

## 💬 社区交流与支持

<div align="center">
  <b>扫描下方二维码加入用户交流群</b><br/>
  <p>分享使用经验、获取最新更新、寻求技术支持</p>
  <img src="./asset/wxqun.png" width="30%" />
</div>

## 🤝 贡献指南

欢迎为IOE项目做出贡献！您可以通过以下方式参与：

1. 提交Bug或功能建议：通过GitHub Issues
2. 提交代码：Fork项目，创建Pull Request
3. 完善文档：改进使用手册和开发文档
4. 分享使用经验：在交流群中与其他用户分享

## 📄 许可证

本项目采用 [MIT License](LICENSE)

## ☕ 支持项目

如果您觉得这个项目对您有帮助，可以通过以下方式支持我们继续开发和维护：

<div align="center">
  <img src="./asset/buyme.jpg" width="30%" /> &nbsp;&nbsp;&nbsp; <img src="./asset/wechat.jpg" width="30%" />
</div>

<div align="center">
  <h3>🙏 特别鸣谢</h3>
  <p>感谢以下用户对本项目的支持：</p>
  <p>
    "挨踢大哥" &nbsp;|&nbsp; "桂教助考网"
  </p>
</div>

## 📞 联系方式

<div align="center">
  <p><b>有问题？建议？或定制化需求？</b></p>
  <p>通过以下方式联系我们：</p>
  <p>
    📧 邮箱：<a href="mailto:zhtyyx@gmail.com">zhtyyx@gmail.com</a><br/>
    🐞 问题反馈：<a href="https://github.com/zhtyyx/ioe/issues">GitHub Issues</a><br/>
    💬 交流群：<a href="#社区交流与支持">扫描上方二维码</a>
  </p>
</div>

---

<div align="center">
  软件著作权已登记，如有疑问请联系我们。<br/>
  Copyright © 2025-2026 IOE Team. All Rights Reserved.
</div>
