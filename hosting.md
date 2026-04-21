# NeuralQueue Hosting Strategy: 100% Free Tier Stack

NeuralQueue is designed to run efficiently on distributed free-tier cloud providers. Follow this roadmap to deploy the full system.

## 1. Cloud Stack Overview
| Component | Provider | Tier Details |
| :--- | :--- | :--- |
| **Frontend** | [Vercel](https://vercel.com) | Hobby Tier (Edge Network, Fast Refresh) |
| **Backend (API)** | [Render](https://render.com) | Free Web Service (Auto-sleeps after 15m) |
| **Database (Postgres)** | [Neon](https://neon.tech) | Free Tier (Auto-scaling, Branching) |
| **Queue (Redis)** | [Upstash](https://upstash.com) | Free Tier (Serverless, 10k requests/day) |
| **Storage (S3/R2)** | [Cloudflare R2](https://cloudflare.com/r2) | Free Tier (10GB storage, $0 Egress) |

---

## 2. Environment Configuration

### Backend (.env)
```env
# Database
DATABASE_URL=postgresql://user:pass@ep-hostname.neon.tech/neondb?sslmode=require

# Redis (Upstash)
REDIS_URL=rediss://default:pass@region.upstash.io:6379

# Storage (Cloudflare R2)
S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
S3_ACCESS_KEY=<your-access-key>
S3_SECRET_KEY=<your-secret-key>
S3_BUCKET_NAME=neural-queue-attachments
S3_PUBLIC_URL=https://pub-your-id.r2.dev

# Security
SECRET_KEY=generate-a-secure-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Frontend (.env)
```env
VITE_API_URL=https://your-backend-render.com
VITE_WS_URL=wss://your-backend-render.com/ws/events
```

---

## 3. Deployment Steps

### Step 1: Database (Neon)
1. Create a Neon project.
2. Run migrations: `alembic upgrade head`.

### Step 2: Storage (Cloudflare R2)
1. Create a bucket named `neural-queue-attachments`.
2. Enable "Public Access" and "CORS" for the frontend domain.

### Step 3: Backend (Render)
1. Connect GitHub repo.
2. Set Build Command: `pip install -r requirements.txt`.
3. Set Start Command: `uvicorn backend.app:app --host 0.0.0.0 --port $PORT`.

### Step 4: Frontend (Vercel)
1. Connect GitHub repo.
2. Vercel will automatically detect Vite and deploy.
3. Configure Environment Variables in the Vercel dashboard.

> [!TIP]
> Since Render Free Tier sleeps, the first request may take ~30s. Use a cron-job (like [Cron-job.org](https://cron-job.org)) to ping the `/health` endpoint once every 14 minutes.
