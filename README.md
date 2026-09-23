# IOE Inventory Management System

[简体中文](README_zh.md) · [Docker guide](README.docker_en.md) · [Issues](https://github.com/zhtyyx/ioe/issues)

IOE is a Django application for small retail stores to manage products, stock, sales, members, and reports. It runs with SQLite by default and can be started locally without a separate database service.

![IOE dashboard](asset/ioe_dashboard_en.png)

## What works today

| Area | Available features |
| --- | --- |
| Products | Categories, barcodes, prices, preset colors and sizes, images, and a detail page |
| Stock | Stock in, stock out, adjustments, low-stock warnings, transaction history, and stocktaking |
| Sales | Checkout, payment methods, member discounts, balance payments, and sales history |
| Members | Levels, recharge, balance and points management, birthday reminders, and member import/export |
| Administration | Reports, user permissions, operation logs, and backup management |

Product bulk import/export, custom color and size options, and returns for completed sales are still open in [issue #34](https://github.com/zhtyyx/ioe/issues/34). Draft sales can be cancelled; this is not a return or refund workflow.

## Screenshots

![Product list](asset/ioe_products_en.png)

![Inventory list](asset/ioe_inventory_en.png)

![Sales checkout](asset/ioe_checkout_en.png)

## Run locally

Use Python 3.10 or newer. The Docker image uses Python 3.10.

1. Clone the repository and create a virtual environment:

   ```bash
   git clone https://github.com/zhtyyx/ioe.git
   cd ioe
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   These commands use a POSIX shell. On Windows, activate the environment with `.venv\Scripts\activate` and create the `db` directory before migration.

2. Install dependencies and initialize SQLite:

   ```bash
   python -m pip install -r requirements.txt
   mkdir -p db
   python manage.py migrate
   python manage.py createsuperuser
   ```

3. Start the development server:

   ```bash
   python manage.py runserver
   ```

Open <http://127.0.0.1:8000/> and sign in with the account created above. The database file is `db/db.sqlite3`. Uploaded files are stored in `media/`.

`runserver` is for local development. For container setup, environment variables, and deployment limitations, follow the [Docker guide](README.docker_en.md).

## Run tests

```bash
python manage.py test inventory.tests
```

The current suite has four pre-existing failures in older integration/view tests. See their assertions before treating a full-suite failure as a regression.

## Project layout

```text
inventory/          Django settings, models, views, templates, and tests
asset/              README screenshots
Dockerfile           Container image
docker-compose.yml  Local Compose configuration
docker-compose.prod.yml  Production example
requirements.txt     Python dependencies
manage.py            Django management commands
```

## Contributing

Open an [issue](https://github.com/zhtyyx/ioe/issues) for a bug or feature request. Keep pull requests focused, include tests for stock, sales, balance, and backup changes, and attach screenshots for visible UI changes.

IOE is released under the [MIT License](LICENSE).
