# El Tablón Albiceleste

Plataforma deportiva argentina multideporte enfocada en agenda, resultados y cobertura de competencia argentina, selecciones y argentinos en el exterior.

## Estado actual

Hoy el proyecto ya tiene:

- frontend desplegado en Vercel
- backend desplegado en Railway
- proxy frontend → backend
- página `/hoy` operativa
- páginas visibles por secciones como:
  - `/hoy`
  - `/resultados`
  - `/deporte/futbol`
  - `/deporte/basquet`

El proyecto todavía está en evolución:
- parte del scraping ya entrega datos reales
- la calidad de competencia/horarios depende todavía de la calidad de algunas fuentes upstream
- hay deportes mejor cubiertos que otros
- quedan pendientes mejoras de relevancia, jerarquía y cobertura fina

## Stack real

### Frontend
- Next.js / App Router
- CSS Modules
- proxy de API desde frontend hacia backend

### Backend
- FastAPI
- caché interna
- bridge hacia paquete `scraping`
- endpoints de health/debug
- deploy en Railway

### Scraping
El proyecto usa un paquete `scraping` separado, con adapters y fuentes por deporte.

Cobertura observada hoy:
- fútbol
- motorsport
- tenis
- básquet
- rugby
- hockey
- vóley
- handball
- futsal
- golf
- boxeo
- MotoGP
- polo
- esports
- dakar / olímpicos con cobertura más limitada o parcial

## Estructura principal

```text
backend/
frontend/
scraping/
