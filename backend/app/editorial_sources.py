"""Matriz editorial de fuentes por deporte para Argentina.

Este módulo centraliza fuentes recomendadas por prioridad:
- official
- trusted_alternative
- fallback

También incluye campos de estado para fases pendientes de validación.
"""

from __future__ import annotations

from typing import Any

SOURCE_MATRIX_VERSION = "2026-04-23"

SOURCE_MATRIX: dict[str, Any] = {
    "meta": {
        "version": SOURCE_MATRIX_VERSION,
        "scope": "Core fase 1 + Polo + Esports; fase 2/3 parcialmente pendientes",
        "priority_order": ["official", "trusted_alternative", "fallback"],
    },
    "sports": {
        "futbol": {
            "selecciones": {
                "official": [
                    "https://www.afa.com.ar/",
                    "https://www.afa.com.ar/fixture/posts/tags?s=seleccion-argentina",
                ],
                "trusted_alternative": [
                    "https://www.espn.com.ar/futbol/",
                    "https://www.promiedos.com.ar/",
                ],
                "fallback": [
                    "https://www.api-football.com/",
                    "https://www.sofascore.com/",
                    "https://www.flashscore.com.ar/futbol/",
                ],
            },
            "liga_profesional": {
                "official": [
                    "https://www.ligaprofesional.ar/",
                    "https://www.ligaprofesional.ar/ficha-partido",
                ],
                "official_support": ["https://www.afa.com.ar/731/pages/estadisticas-primera-division"],
                "trusted_alternative": [
                    "https://www.espn.com.ar/futbol/",
                    "https://www.promiedos.com.ar/",
                ],
                "fallback": [
                    "https://www.api-football.com/",
                    "https://www.sofascore.com/",
                    "https://www.flashscore.com.ar/futbol/argentina/",
                ],
            },
            "internacional": {
                "official": ["https://www.conmebol.com/", "https://www.afa.com.ar/"],
                "trusted_alternative": [
                    "https://www.espn.com.ar/futbol/",
                    "https://www.promiedos.com.ar/",
                ],
                "fallback": [
                    "https://www.api-football.com/",
                    "https://www.sofascore.com/",
                    "https://www.flashscore.com.ar/futbol/",
                ],
                "note": "Conmebol pendiente de validación fina en esta pasada.",
            },
        },
        "tenis": {
            "selecciones": {
                "official": [
                    "https://www.aat.com.ar/",
                    "https://www.itftennis.com/",
                    "https://www.daviscup.com/",
                    "https://www.billiejeankingcup.com/",
                ],
                "trusted_alternative": ["https://www.espn.com.ar/tenis/"],
                "fallback": ["https://www.sofascore.com/", "https://www.flashscore.com.ar/tenis/"],
            },
            "circuitos": {
                "official": [
                    "https://www.atptour.com/es",
                    "https://www.wtatennis.com/",
                    "https://www.itftennis.com/",
                ],
                "official_local": [
                    "https://www.aat.com.ar/",
                    "https://deportivaoat.com.ar/sis/app/vTorneo.php",
                ],
            },
        },
        "basquet": {
            "selecciones": {
                "official": ["https://www.argentina.basketball/", "https://www.fiba.basketball/"],
                "trusted_alternative": ["https://www.espn.com.ar/basquet/"],
                "fallback": ["https://www.sofascore.com/", "https://www.flashscore.com.ar/basquetbol/"],
            },
            "ligas": {
                "official": [
                    "https://www.laliganacional.com.ar/laliga/",
                    "https://www.laliganacional.com.ar/ligaargentina/",
                    "https://www.argentina.basketball/",
                ],
            },
        },
        "rugby": {
            "selecciones": {
                "official": ["https://www.urba.org.ar/", "https://www.world.rugby/"],
                "trusted_alternative": [
                    "https://www.espn.com.ar/rugby/",
                    "https://www.aplenorugby.com.ar/",
                ],
                "fallback": ["https://www.sofascore.com/", "https://www.flashscore.com.ar/rugby-union/"],
            }
        },
        "hockey": {
            "selecciones": {
                "official": ["https://www.cahockey.org.ar/", "https://www.fih.hockey/"],
                "trusted_alternative": ["https://www.espn.com.ar/hockey-sobre-cesped/"],
                "fallback": ["https://www.sofascore.com/"],
            }
        },
        "voley": {
            "selecciones": {
                "official": ["https://feva.org.ar/", "https://en.volleyballworld.com/"],
                "trusted_alternative": ["https://www.espn.com.ar/voley/"],
                "fallback": ["https://www.flashscore.com.ar/voleibol/", "https://www.sofascore.com/"],
            },
            "liga_aclav": {
                "official": ["https://www.aclav.com/"],
                "official_support": ["https://feva.org.ar/"],
            },
        },
        "futsal": {
            "estructura": {
                "official": ["https://www.afa.com.ar/"],
                "trusted_alternative": [
                    "https://parenlapelotafutsal.com.ar/",
                    "https://pasionfutsal.com.ar/",
                ],
                "fallback": ["https://www.sofascore.com/"],
            }
        },
        "handball": {
            "selecciones": {
                "official": ["https://handballargentina.org/cah/", "https://www.ihf.info/"],
                "trusted_alternative": ["https://www.sofascore.com/"],
            }
        },
        "motorsport": {
            "f1": {
                "official": [
                    "https://www.formula1.com/",
                    "https://www.formula1.com/en/results.html",
                    "https://api.fia.com/international-sporting-calendar",
                ],
                "trusted_alternative": ["https://www.espn.com.ar/deporte-motor/"],
                "fallback": ["https://www.sofascore.com/"],
            },
            "motogp": {
                "official": ["https://www.motogp.com/", "https://www.motogp.com/en/gp-results"],
                "trusted_alternative": ["https://www.espn.com.ar/deporte-motor/"],
            },
            "actc": {
                "official": [
                    "https://www.actc.org.ar/",
                    "https://www.actc.org.ar/tc/calendario.html",
                    "https://www.actc.org.ar/tc/campeonato.html",
                    "https://www.actc.org.ar/tc/resultados.html",
                ]
            },
        },
        "polo": {
            "torneos": {
                "official": [
                    "https://www.aapolo.com/",
                    "https://www.aapolo.com/calendario/eventos",
                    "https://www.aapolo.com/noticias",
                    "https://www.aapolo.com/palermo",
                    "https://www.aapolo.com/jugadores",
                ],
                "official_support": ["https://www.aapolo.com/bundles/web/files/AAP%20-%20Reglamentos%20tecnicos.pdf"],
            }
        },
        "esports": {
            "actividad_local": {
                "official": ["https://www.deva.org.ar/", "https://www.deva.org.ar/FAE/"],
                "official_support": ["https://www.afa.com.ar/Sitio/posts/lanzamiento-afa-esports-pro-series"],
                "trusted_alternative": ["https://liquipedia.net/", "https://www.vlr.gg/"],
                "fallback": ["https://lol.fandom.com/"],
            }
        },
        "padel": {
            "status": "pending_validation",
            "official": ["https://padel.org.ar/", "https://www.fip-padel.com/"],
            "trusted_alternative": ["https://premierpadel.com/"],
        },
        "boxeo": {
            "status": "pending_validation",
            "official": ["https://www.instagram.com/federacionargentinadebox/"],
            "trusted_alternative": ["https://boxrec.com/", "https://www.tapology.com/"],
        },
        "olimpicos": {
            "status": "pending_validation",
            "official": ["https://www.coarg.org.ar/", "https://olympics.com/"],
        },
    },
}


def list_sports() -> list[str]:
    return sorted(SOURCE_MATRIX.get("sports", {}).keys())


def get_sport_matrix(sport: str) -> dict[str, Any] | None:
    return SOURCE_MATRIX.get("sports", {}).get(sport)
