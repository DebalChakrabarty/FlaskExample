# Tasks API — a Flask app for learning containerized deployment

A deliberately small REST API (create / list / get / delete tasks) whose real
purpose is to teach you how to **package and run an app in Docker** the way
you'd do it for real work.

## What's in here

| File             | Why it matters for deployment                                        |
|------------------|----------------------------------------------------------------------|
| `app.py`         | The Flask app. Config from env vars, `/health` probe, logs to stdout.|
| `requirements.txt` | Pinned deps (Flask + **gunicorn**, a real WSGI server).            |
| `Dockerfile`     | Slim base, layer caching, **non-root user**, healthcheck, gunicorn.  |
| `.dockerignore`  | Keeps the build context small and clean.                             |

## The endpoints

```
GET    /                 # info + endpoint map
GET    /health           # probe target (liveness/readiness)
GET    /api/tasks        # list
POST   /api/tasks        # create   body: {"title": "..."}
GET    /api/tasks/<id>   # fetch one
DELETE /api/tasks/<id>   # delete
```

---

## Run it in Docker (the main event)

**1. Build the image**

```bash
docker build -t tasks-api:0.1.0 .
```

**2. Run a container**

```bash
docker run -d --name tasks -p 8000:8000 tasks-api:0.1.0
```

- `-d` runs it detached (in the background)
- `-p 8000:8000` maps your host's port 8000 to the container's port 8000

**3. Hit it**

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/tasks \
     -H "Content-Type: application/json" \
     -d '{"title":"learn docker"}'
curl http://localhost:8000/api/tasks
```

**4. Look around inside / at the container**

```bash
docker logs tasks            # see the app's stdout logs
docker ps                    # STATUS shows (healthy) once the healthcheck passes
docker exec -it tasks sh     # shell into the running container
```

**5. Clean up**

```bash
docker stop tasks && docker rm tasks
```

---

## Passing configuration (the 12-factor lesson)

The app reads `APP_NAME`, `APP_VERSION`, and `LOG_LEVEL` from the environment.
Override them at run time without rebuilding the image:

```bash
docker run -d --name tasks -p 8000:8000 \
  -e APP_VERSION=1.2.3 -e LOG_LEVEL=DEBUG \
  tasks-api:0.1.0

curl http://localhost:8000/health   # note the version reflects what you passed
```

This is the same idea you'll later use with Kubernetes ConfigMaps/Secrets: the
image is immutable, the config is injected.

---

## Run without Docker (optional, for quick edits)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py        # dev server on http://localhost:8000
```

Note: `python app.py` uses Flask's built-in dev server — fine for local
hacking, **not** for production. The container uses gunicorn instead.

---

## A lesson baked into this app: state and scaling

Tasks are stored **in memory**, so:

- Restarting the container wipes all tasks.
- The Dockerfile runs gunicorn with **one** worker on purpose. Each worker is a
  separate process with its own memory, so multiple workers would see different
  task lists. Try changing `-w 1` to `-w 4`, rebuild, and watch reads become
  inconsistent — that's the whole reason real services push state into a shared
  datastore instead of the app process.

Making this stateless (Postgres or Redis via `docker compose`) is the natural
next exercise.

---

## Where to take it next (toward the bigger roadmap)

1. **`docker compose`** — add a Postgres service and make the API stateless.
2. **Push to a registry** — `docker tag` + `docker push` to Docker Hub or ECR.
3. **CI** — a GitHub Actions workflow that builds and pushes the image on commit.
4. **Kubernetes** — a Deployment + Service, wiring `/health` to liveness and
   readiness probes, and config via ConfigMap. This service is already shaped
   for that (health endpoint, env config, non-root, stdout logs).
