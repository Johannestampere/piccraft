# PicCraft

What if Minecraft could see your world?

Take a photo on your phone and watch it build itself in-game — first as 2D pixel art, then as a 3D relief, and finally as a full AI-generated model.

---

## How it works

1. Open the web app, take or upload a photo
2. The image is sent to the backend pipeline
3. Three stages build progressively in-world, each replacing the last:
   - **Stage 0 — Mosaic** (~5s): dithered 2D block billboard
   - **Stage 1 — Depth 3D** (~30s): depth-extruded voxel relief using Depth Anything V2
   - **Stage 2 — Tripo 3D** (~90s): full AI-generated 3D mesh via Tripo API, voxelized into blocks
4. The Paper plugin polls the backend and places each stage tick-safely as it completes

---

## Stack

| Layer | Tech |
|---|---|
| Web app | Vanilla HTML/JS, deployed on Vercel |
| Backend | Python + FastAPI + Celery + Redis + Docker |
| AI pipeline | Depth Anything V2, Tripo AI, segment-anything |
| Minecraft | Paper 1.21.4 plugin (Java) |

---

## Project structure

```
backend/          FastAPI app + Celery pipeline
minecraft-plugin/ Paper plugin source (Gradle)
paper-server/     Paper server config and plugins
web/              Web camera app (static HTML)
docker-compose.yml
```

---

## Running locally

### 1. Backend

```bash
cp backend/.env.example backend/.env
# Add TRIPO_API_KEY to .env (optional, but Stage 2 is skipped without it)

docker compose up
```

FastAPI runs at `http://localhost:8000`. Worker restarts required after code changes:
```bash
docker compose restart worker
```

### 2. Minecraft server

```bash
cd paper-server
java -jar paper.jar --nogui
```

Plugin config at `paper-server/plugins/PicCraft/config.yml`:
```yaml
backend-url: http://localhost:8000
poll-interval-seconds: 3
blocks-per-tick: 200
forward-offset: 5
```

### 3. Web app

Open `web/index.html` directly, or deploy to Vercel.

Update the `BACKEND` constant in `web/index.html` to point at your backend (use [ngrok](https://ngrok.com) to expose localhost):
```js
const BACKEND = 'https://your-ngrok-url.ngrok-free.app';
```

---

## Building the plugin

```bash
cd minecraft-plugin
./gradlew clean build
cp build/libs/PicCraft-0.1.0.jar ../paper-server/plugins/
# Restart the Paper server
```

---

## Plugin commands

| Command | Description |
|---|---|
| `/picclear [last\|job_id]` | Clear a placed build |
| `/piccmove [last\|job_id]` | Move a build to your current position |

---

## Test upload

```bash
curl -X POST http://localhost:8000/api/v0/jobs \
  -F "file=@/path/to/image.jpg"
```