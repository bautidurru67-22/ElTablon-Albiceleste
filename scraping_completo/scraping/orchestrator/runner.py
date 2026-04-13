"""
Runner — punto de entrada para ejecutar el scraping completo o por deporte.
Uso CLI:
    python -m scraping.orchestrator.runner
    python -m scraping.orchestrator.runner --sport futbol
    python -m scraping.orchestrator.runner --sport futbol tenis
    python -m scraping.orchestrator.runner --only-argentina
"""
import asyncio
import json
import argparse
import logging
from scraping.orchestrator.coordinator import ScrapingCoordinator
from scraping.registry import ADAPTER_REGISTRY

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


async def run(
    sports: list[str] | None = None,
    only_argentina: bool = True,
    as_backend_dicts: bool = True,
) -> list[dict] | list:
    """
    Ejecuta scraping y retorna resultados.

    Args:
        sports: lista de deportes a correr. None = todos.
        only_argentina: filtrar solo partidos con argentina_relevance != "none".
        as_backend_dicts: convertir a dicts compatibles con el backend FastAPI.
    """
    adapters = ADAPTER_REGISTRY
    if sports:
        adapters = {k: v for k, v in adapters.items() if k in sports}

    coordinator = ScrapingCoordinator(adapters)
    flat = await coordinator.run_all_flat()

    if only_argentina:
        flat = coordinator.get_argentina_matches(flat)

    logger.info(f"[runner] total: {len(flat)} partidos")

    if as_backend_dicts:
        return [m.to_backend_dict() for m in flat]
    return flat


def main():
    parser = argparse.ArgumentParser(description="El Tablón Albiceleste — Scraping runner")
    parser.add_argument("--sport", nargs="+", help="Deportes a correr (default: todos)")
    parser.add_argument("--all", action="store_true", help="Incluir partidos sin relevancia ARG")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    results = asyncio.run(
        run(
            sports=args.sport,
            only_argentina=not args.all,
        )
    )

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False, default=str))
    else:
        for r in results:
            status = r.get("status", "?").upper()
            sport = r.get("sport", "?")
            home = r.get("home_team", "?")
            away = r.get("away_team", "?")
            score = ""
            if r.get("home_score") is not None:
                score = f"  {r['home_score']}-{r['away_score']}"
            relevance = r.get("argentina_relevance", "none")
            print(f"[{status:8}] {sport:10} | {home} vs {away}{score}  ({relevance})")


if __name__ == "__main__":
    main()
