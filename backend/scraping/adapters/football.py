import httpx
from datetime import datetime
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch


class FootballAdapter(BaseScraper):
    async def scrape(self):
        matches = []

        url = "https://www.espn.com.ar/futbol/agenda"

        async with httpx.AsyncClient(timeout=20) as client:
            try:
                res = await client.get(url)
                html = res.text
            except Exception as e:
                print(f"[football] error request: {e}")
                return []

        # ⚠️ Esto es parsing simple para forzar data real
        if "Argentina" not in html:
            print("[football] no se detectó contenido esperado")
            return []

        # 👉 mock REALISTA temporal basado en agenda real
        # (sirve para validar sistema completo)

        matches.append(
            NormalizedMatch(
                id="test-boca-river",
                sport="futbol",
                competition="Liga Argentina",
                home_team="Boca Juniors",
                away_team="River Plate",
                home_score=None,
                away_score=None,
                status="upcoming",
                minute=None,
                datetime_utc=None,
                start_time_arg="21:30",
                argentina_relevance="club_arg",
                argentina_team="Boca Juniors",
                broadcast="ESPN",
            )
        )

        matches.append(
            NormalizedMatch(
                id="test-inter-miami",
                sport="futbol",
                competition="MLS",
                home_team="Inter Miami",
                away_team="LA Galaxy",
                home_score=1,
                away_score=0,
                status="live",
                minute="67'",
                datetime_utc=None,
                start_time_arg="20:00",
                argentina_relevance="jugador_arg",
                argentina_team="Lionel Messi",
                broadcast="Apple TV",
            )
        )

        print(f"[football] matches generados: {len(matches)}")

        return matches
