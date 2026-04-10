# El Tablón Albiceleste

> **"Donde juega Argentina"** — Plataforma de información deportiva argentina en tiempo real.

---

## Stack

| Parte | Tecnología |
|---|---|
| Frontend | Next.js 14 (App Router, Server Components) |
| Backend | FastAPI + APScheduler + MemoryCache |
| Scraping | Python async — Promiedos, ATP Tour, FIH, UAR, LNB, OpenF1 |
| Deploy recomendado | Vercel (frontend) + Railway (backend) |

---

## Estructura

```
tablon-albiceleste/
├── frontend/           Next.js
├── backend/            FastAPI
├── scraping/           Adapters por deporte
├── Dockerfile          Backend + scraping (para Railway/Render)
├── docker-compose.yml  Dev local full-stack
├── railway.json        Config Railway
├── render.yaml         Config Render
└── validate_deploy.sh  Script de validación post-deploy
```

---

## Deploy en producción

### Backend — Railway (recomendado)

1. Crear cuenta en [railway.app](https://railway.app)
2. "New Project" → "Deploy from GitHub repo"
3. Seleccionar este repositorio, Railway detecta el `Dockerfile` raíz
4. Agregar variables de entorno en Railway Dashboard:

```
ENVIRONMENT=production
FRONTEND_URL=https://TU_FRONTEND.vercel.app
LOG_LEVEL=INFO
SCRAPING_ENABLED=true
```

5. Railway asigna una URL pública automáticamente: `https://tablon-albiceleste-api.up.railway.app`

#### Alternativa: Render

1. "New Web Service" → conectar repo
2. Render detecta `render.yaml` automáticamente
3. Actualizar `FRONTEND_URL` en la variable de entorno

---

### Frontend — Vercel

1. Ir a [vercel.com](https://vercel.com) → "Add New Project"
2. Importar este repositorio
3. **Root Directory:** `frontend`
4. Agregar variable de entorno en Vercel:

```
NEXT_PUBLIC_API_URL=https://TU_BACKEND.up.railway.app
```

5. Deploy — Vercel asigna `https://tablon-albiceleste.vercel.app`

6. **Importante:** volver al backend (Railway/Render) y actualizar `FRONTEND_URL` con la URL de Vercel real.

---

## Variables de entorno

### Backend (Railway / Render)

| Variable | Requerida | Ejemplo |
|---|---|---|
| `ENVIRONMENT` | ✅ | `production` |
| `FRONTEND_URL` | ✅ | `https://tablon-albiceleste.vercel.app` |
| `LOG_LEVEL` | — | `INFO` |
| `SCRAPING_ENABLED` | — | `true` |
| `PORT` | auto | Railway lo inyecta automáticamente |

### Frontend (Vercel)

| Variable | Requerida | Ejemplo |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | ✅ | `https://tablon-albiceleste-api.up.railway.app` |

---

## Setup local (sin Docker)

```bash
# Terminal 1 — Backend
cd backend
pip install -r requirements.txt
cp .env.example .env          # editar si hace falta
uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm install
cp .env.example .env.local    # editar NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

## Setup local (con Docker)

```bash
docker-compose up --build
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

---

## Endpoints

| Endpoint | Descripción |
|---|---|
| `GET /api/health` | Health básico |
| `GET /api/health/full` | Estado scheduler + cache |
| `GET /api/matches/live` | Partidos en vivo |
| `GET /api/matches/today` | Agenda del día |
| `GET /api/matches/results` | Resultados finalizados |
| `GET /api/matches/argentina` | Solo partidos ARG |
| `GET /api/matches/club/{id}` | Partidos de un club |
| `GET /api/sports/` | Resumen por deporte |
| `GET /api/players/abroad` | Argentinos en el mundo |

Todos los endpoints de `/matches` aceptan `?sport=futbol`.

---

## Validación post-deploy

```bash
# Validar backend
./validate_deploy.sh https://TU_BACKEND.up.railway.app

# Manual
curl https://TU_BACKEND.up.railway.app/api/health
curl https://TU_BACKEND.up.railway.app/api/matches/argentina
```

---

## Redeploy

**Railway:** push a `main` → deploy automático.
**Vercel:** push a `main` → deploy automático.
**Manual Railway:** en el dashboard → "Redeploy".

---

## Páginas del sitio

| URL | Vista |
|---|---|
| `/hoy` | Argentinos en acción hoy (hub principal) |
| `/calendario` | Agenda del día con selector de días |
| `/resultados` | Scores finalizados agrupados |
| `/deporte/futbol` | Vista de fútbol argentino |
| `/deporte/tenis` | Vista de tenis argentino |
| `/deporte/[sport]` | Cualquier deporte del nav |
| `/club/river-plate` | Club view dinámica |
| `/club/[id]` | Cualquier club |

---

## Estado del sistema

- [x] Frontend: 6 páginas + componentes
- [x] Backend: FastAPI + scheduler + cache + mock fallback
- [x] Scraping: 5 reales (football, tennis, basketball, rugby, hockey) + 11 stubs
- [x] Deploy: Dockerfile + railway.json + render.yaml
- [ ] Base de datos persistente (Prompt 7+)
- [ ] Autenticación (Prompt 7+)
