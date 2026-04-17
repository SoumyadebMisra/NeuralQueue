# NeuralQueue++

**NeuralQueue++** is a distributed AI workload orchestration system that simulates how modern cloud platforms (like Azure ML / Service Bus) schedule, execute, and monitor large-scale inference jobs.

---

# 🚀 Overview

NeuralQueue++ allows users to submit AI tasks (e.g., summarization, embeddings, image captioning), which are:

* queued using Redis Streams
* scheduled using a priority + cost-aware algorithm
* executed by distributed workers
* monitored via a real-time dashboard

---

# 🧠 Key Features

## 1. Distributed Task Scheduling

* Priority-aware queues (CRITICAL, HIGH, MEDIUM, LOW)
* Weighted Priority + Shortest Job First (WP-SJF)
* Anti-starvation via aging

## 2. Scalable Worker Pool

* Stateless workers
* Horizontal scaling support
* Worker heartbeat + health tracking

## 3. Resource-Aware Execution

* Simulated GPU budget per worker
* Tasks require GPU cost
* Scheduler assigns tasks based on available capacity

## 4. Fault Tolerance

* Retry mechanism
* Dead Letter Queue (DLQ)
* At-least-once processing semantics

## 5. Real-Time Observability

* Live dashboard (React + WebSockets)
* Metrics: queue depth, latency, throughput
* Worker utilization tracking

---

# 🏗️ Architecture

```
Client (UI)
   ↓
API Gateway (FastAPI)
   ↓
Redis Streams (Priority Queues)
   ↓
Scheduler Service
   ↓
Worker Pool
   ↓
Database (PostgreSQL)
```

---

# 🔄 Data Flow

1. User submits task via UI or API
2. API stores task and pushes to Redis Stream
3. Scheduler pulls tasks and assigns priority score
4. Worker consumes task and executes it
5. Result is stored and broadcast via WebSocket
6. UI updates in real-time

---

# 🧩 Tech Stack

| Layer      | Technology          |
| ---------- | ------------------- |
| Backend    | FastAPI (Python)    |
| Queue      | Redis Streams       |
| Workers    | Python (asyncio)    |
| Database   | PostgreSQL          |
| Frontend   | React               |
| Realtime   | WebSockets          |
| Metrics    | Prometheus          |
| Deployment | Docker / Kubernetes |

---

# ⚙️ Getting Started

## 1. Clone Repo

```
git clone <repo-url>
cd neuralqueue
```

## 2. Run with Docker

```
docker-compose up --build
```

## 3. Start Frontend

```
cd frontend
npm install
npm start
```

---

# 📡 API Endpoints

## Auth

* `POST /auth/login`
* `POST /auth/register`

## Tasks

* `POST /tasks` — submit task
* `GET /tasks` — list tasks
* `GET /tasks/{id}` — task details
* `DELETE /tasks/{id}` — cancel task

## Workers

* `GET /workers` — worker status

## Metrics

* `GET /metrics`

## WebSocket

* `/ws/events`

---

# 🧪 Example Task

```json
{
  "type": "summarization",
  "priority": "HIGH",
  "gpu_budget": 40,
  "payload": {
    "text": "..."
  }
}
```

---

# 📊 Metrics Tracked

* Queue depth
* Task latency (P50, P95, P99)
* Throughput (tasks/sec)
* Worker utilization
* Failure rate

---

# 🔐 Authentication

* JWT-based authentication for UI users
* API keys for programmatic access
* Multi-tenant task isolation

---

# 🎯 Design Decisions

## Why Redis Streams?

* Persistent
* Consumer groups
* Built-in retry semantics

## Why FastAPI?

* Async support
* Fast development
* WebSocket support

## Why Separate Scheduler?

* Decouples logic from workers
* Enables smarter scheduling policies

---

# 🚀 Future Improvements

* Multi-region deployment
* Leader election (Raft-lite)
* Cost-based scheduling (spot vs on-demand)
* ML-based adaptive scheduling
* Kubernetes auto-scaling

---

# 🧠 Interview Talking Points

* Distributed scheduling with WP-SJF
* At-least-once delivery + idempotency
* Resource-aware task assignment
* Backpressure handling via queue depth
* Separation of control plane vs data plane

---

# 📌 Summary

NeuralQueue++ demonstrates:

* distributed systems design
* scalable backend architecture
* real-time observability
* production-grade engineering thinking

---

# 👤 Author

Soumyadeb Misra

---

⭐ If you found this project interesting, feel free to star the repo!
