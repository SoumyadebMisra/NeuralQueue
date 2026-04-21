# Deploying NeuralQueue Backend to Render

This guide provides step-by-step instructions for deploying the NeuralQueue orchestrator to Render.

## 1. Prerequisites
- A [Render](https://render.com) account.
- Your project pushed to a GitHub or GitLab repository.
- Active instances of **Neon Postgres** and **Upstash Redis**.

## 2. Render Configuration

### Web Service Settings
| Setting | Value |
| :--- | :--- |
| **Runtime** | `Python 3.x` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn backend.app:app --host 0.0.0.0 --port $PORT` |
| **Root Directory** | `backend` |

### Environment Variables
Add the following variables in the Render Dashboard (Environment tab):

| Variable | Source / Example |
| :--- | :--- |
| `DATABASE_URL` | Your Neon Postgres connection string |
| `REDIS_HOST` | `inspired-gobbler-104133.upstash.io` |
| `REDIS_PORT` | `6379` (or the port provided by Upstash) |
| `REDIS_PASSWORD` | Your Upstash Redis password |
| `REDIS_TLS` | `true` (Mandatory for Upstash) |
| `PYTHON_VERSION` | `3.12.4` (Matching your local environment) |

## 3. Database Migrations
Since NeuralQueue uses SQLAlchemy/Alembic, you need to run migrations on the production database. You can do this by adding a pre-deploy command or running it manually from the Render shell:

```bash
alembic upgrade head
```

## 4. Scaling & Performance
- **Workers**: The current orchestrator is designed to handle concurrency internally via `asyncio`. A single Render instance can handle significant load.
- **Health Check**: Set the health check path to `/` or `/api/v1/tasks/models` to ensure Render knows when your service is live.

## 5. Troubleshooting
- **ModuleNotFoundError**: Ensure the **Root Directory** is set to `backend`. If you leave it as the project root, the imports like `from backend.app import app` will fail.
- **Redis Connection**: If the worker fails to start, verify that `REDIS_TLS` is set to `true`. Upstash requires encrypted connections.
