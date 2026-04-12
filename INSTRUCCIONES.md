# INSTRUCCIONES DE INTEGRACIÓN
# El Tablón Albiceleste — Backend Scraping

## QUÉ TOCAR EN TU REPO

### 1. Archivos a REEMPLAZAR en tu repo

Encontrá en tu repo los archivos equivalentes a estos y reemplazalos:

| Archivo generado           | Qué reemplaza en tu repo              |
|---------------------------|---------------------------------------|
| `scrapers/api_sports_base.py` | Tu archivo base/utils de scrapers  |
| `scrapers/football.py`    | Tu scraper de fútbol actual           |
| `scrapers/tennis.py`      | Tu scraper de tenis actual            |
| `scrapers/basketball.py`  | Tu scraper de básquet actual          |
| `scrapers/rugby.py`       | Tu scraper de rugby actual            |
| `scrapers/hockey.py`      | Tu scraper de hockey actual           |
| `scrapers/volleyball.py`  | Tu scraper de vóley actual            |
| `scrapers/futsal.py`      | Tu scraper de futsal actual           |
| `scrapers/registry.py`    | Tu orquestador/registry actual        |
| `api_hoy.py`              | Tu router/endpoint de /api/hoy        |
| `.env.example`            | Tu .env.example                       |

### 2. El único cambio CRÍTICO (fecha ART)

Si en tu repo existe algo así:

```python
# ESTO ESTÁ MAL — usa UTC
from datetime import datetime
today = datetime.now().strftime("%Y-%m-%d")
today = datetime.utcnow().strftime("%Y-%m-%d")
```

Reemplazalo con esto:

```python
# CORRECTO — usa ART (UTC-3)
from datetime import datetime, timezone, timedelta
ART = timezone(timedelta(hours=-3))
today = datetime.now(ART).strftime("%Y-%m-%d")
```

Buscá este patrón en TODOS los archivos de tu backend.

### 3. `__init__.py` del paquete scrapers

Asegurate de tener esto en `scrapers/__init__.py`:

```python
from .registry import run_sport, run_all, get_today_summary
```

### 4. Integrar el router en tu main app

Si usás FastAPI:

```python
# main.py o app.py
from fastapi import FastAPI
from api_hoy import router

app = FastAPI()
app.include_router(router)
```

Si ya tenés el router, solo actualizá las funciones que llama — no toques las rutas.

### 5. Dependencias nuevas a agregar en requirements.txt

```
httpx>=0.27.0
```

Si ya tenés `httpx`, no necesitás hacer nada.

---

## DIAGNÓSTICO DE TUS 4 PROBLEMAS

### Problema 1 — "sábado 11" cuando es "domingo 12"

**Causa:** El backend genera la fecha con `datetime.utcnow()` o `datetime.now()` sin timezone.
A las 00:30 UTC → en ART son las 21:30 del día anterior.

**Fix:** Buscar y reemplazar TODO uso de `datetime.now()` sin timezone.
Ver sección 2 arriba.

### Problema 2 — `/deporte/tenis`, `/deporte/futbol` etc dan timeout

**Causa:** Cada página de deporte hace su propio scraping fresco.
Con Railway free tier: cold start (3s) + 4 fuentes en paralelo (8s) = 11s+, Vercel corta a 10s.

**Fix real:** Las páginas de deporte NO deben hacer scraping propio.
Deben leer del caché que ya llenó `/api/hoy`.

En tu frontend (Next.js):
```typescript
// app/deporte/[sport]/page.tsx — CAMBIAR ESTO:
// const data = await fetch(`/api/scrape/${sport}`)  // ← hace scraping nuevo

// POR ESTO:
const data = await fetch(`/api/hoy?sport=${sport}`)  // ← lee caché existente
```

O en el backend, el endpoint `/api/deporte/:sport` debe llamar `run_sport(sport)`
que internamente usa caché — NO debe hacer un scraping desde cero.

### Problema 3 — `/calendario` y `/resultados` vacíos

**Causa:** Son endpoints independientes que no comparten caché con `/api/hoy`.

**Fix:** Ambos deben llamar `get_today_summary()` (que tiene caché) y filtrar.
El `api_hoy.py` generado ya implementa esto correctamente.

### Problema 4 — Hockey, vóley, futsal vacíos

**Causa:** El bug principal estaba en el slug de Sofascore:
- Hockey usaba `"ice-hockey"` en vez de `"field-hockey"` → 0 resultados
- Vóley: filtro de país demasiado estricto
- Futsal: mismo issue de fecha UTC

**Fix:** Los 3 scrapers generados usan el slug correcto y timezone ART.

---

## VALIDACIÓN POST-DEPLOY

Después de subir los cambios, verificar:

```bash
# 1. Timezone correcto
curl https://tu-backend.railway.app/api/health
# Debe mostrar today_art = fecha de HOY en Argentina

# 2. Fútbol con datos reales
curl https://tu-backend.railway.app/api/hoy | python3 -m json.tool | grep -E '"status"|"competition"'

# 3. Tenis con jugadores ARG
curl https://tu-backend.railway.app/api/deporte/tenis | python3 -m json.tool | grep '"home_team"'

# 4. Sin timeout en deportes individuales
time curl https://tu-backend.railway.app/api/deporte/basquet
# Debe responder en < 3 segundos (desde caché)
```

---

## NOTAS IMPORTANTES

- Los scrapers usan **solo fuentes públicas sin auth** (Sofascore, ESPN, Fotmob)
- Si agregás `API_FOOTBALL_KEY` en Railway → activás la fuente más rica automáticamente
- El caché es en memoria (no Redis) — se reinicia con cada deploy. Para persistencia, agregar Redis plugin en Railway
- Todos los logs van con `logging` — en Railway se ven en el tab "Logs"
