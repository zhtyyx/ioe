# Docker Deployment Guide

This document provides detailed instructions for deploying this application using Docker.

## Prerequisites

- Install [Docker](https://docs.docker.com/get-docker/)
- Install [Docker Compose](https://docs.docker.com/compose/install/)

## Development Environment Deployment

1. Clone the repository

```bash
git clone <repository-url>
cd ioe
```

2. Create environment variable file

```bash
cp .env.template .env
# Edit the .env file and fill in the correct configuration information
```

3. Build and start containers

```bash
docker-compose up --build
```

4. Access the application

Open your browser and visit http://localhost:8000

## Production Environment Deployment

1. Clone the repository

```bash
git clone <repository-url>
cd ioe
```

2. Create environment variable file

```bash
cp .env.template .env
# Edit the .env file and fill in the correct configuration information, especially SECRET_KEY and ALLOWED_HOSTS
```

3. Start containers with production configuration

```bash
docker-compose -f docker-compose.prod.yml up -d
```

4. Create a superuser (if needed)

```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

## Data Persistence

In the production environment, data is stored in Docker volumes:

- `static_volume`: Static files
- `media_volume`: Media files (such as uploaded images)
- `db_volume`: Database files

## Common Commands

- View logs: `docker-compose logs -f`
- Stop services: `docker-compose down`
- Restart services: `docker-compose restart`
- Execute Django management commands: `docker-compose exec web python manage.py <command>`

## Custom Configuration

To customize Docker configuration, you can edit the following files:

- `Dockerfile`: Modify the application environment
- `docker-compose.yml`: Modify development environment service configuration
- `docker-compose.prod.yml`: Modify production environment service configuration

## Important Notes

1. In the production environment, make sure to set a secure SECRET_KEY
2. Update ALLOWED_HOSTS to include your domain name
3. Consider using an external database service (such as PostgreSQL) instead of SQLite for better performance
4. Regularly backup data in volumes