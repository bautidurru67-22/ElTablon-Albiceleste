"""
Fútbol argentino robusto y flexible.

Objetivo:
- que fútbol nazca bien filtrado desde origen
- evitar falsos positivos tipo Arsenal / Tigres / Union Omaha
- cubrir realmente el universo de fútbol argentino relevante
- priorizar:
    1) Selección argentina
    2) Clubes argentinos reales
    3) Competiciones locales argentinas
    4) Copas CONMEBOL con clubes argentinos
- mantener múltiples fuentes, con filtro editorial fuerte pero no excesivamente rígido

Cobertura editorial buscada:
- Selección mayor masculina y femenina
- Juveniles / Sub-17 / Sub-20 / Sub-23
- Liga Profesional
- Primera Nacional
- Copa Argentina
- Reserva
- Primera División Femenina
- B Metro
- Federal A
- Federal B / Regional / torneos federales equivalentes si aparecen en fuentes
- Primera C
- Promocional Amateur si aparece
- Copa Libertadores
- Copa Sudamericana
- Mundial / Eliminatorias / amistosos / copas de selección relevantes
"""

from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.sources.promiedos import get_today_html, parse_matches
from scraping.sources.afa import get_fixture_html, parse_fixture as parse_afa_fixture
from scraping.sources.api_football import get_fixtures_today, parse_fixture as parse_api_football
from scraping.normalizers.promiedos_normalizer import normalize_matches as normalize_promiedos
from scraping.sources.sofascore import get_events_by_date, get_live_events
from scraping.normalizers import sofascore_normalizer
from scraping.argentina import normalize_str

logger = logging.getLogger(__name__)


class FootballAdapter(BaseScraper):
    SOURCE_ORDER = ["promiedos", "afa", "api_football", "sofascore", "espn"]
    DIAG_VERSION = "football-flex-v2-2026-04-15"
    LAST_RUN: dict = {}

    # Competiciones locales / argentinas que queremos dejar pasar
    TRUSTED_LOCAL_COMPETITIONS = {
        "liga profesional",
        "liga profesional argentina",
        "torneo betano",
        "primera division",
        "primera división",
        "primera nacional",
        "nacional b",
        "b nacional",
        "primera b",
        "primera b metropolitana",
        "b metro",
        "primera c",
        "primera d",
        "promocional amateur",
        "federal a",
        "federal b",
        "torneo federal",
        "regional amateur",
        "copa argentina",
        "copa de la liga",
        "supercopa argentina",
        "supercopa internacional",
        "trofeo de campeones",
        "reserva",
        "torneo de reserva",
        "primera femenina",
        "primera division femenina",
        "primera división femenina",
        "futbol femenino",
        "fútbol femenino",
        "juveniles afa",
        "juveniles",
    }

    # Copas internacionales donde juegan clubes argentinos
    TRUSTED_INTL_COMPETITIONS = {
        "conmebol libertadores",
        "copa libertadores",
        "libertadores",
        "conmebol sudamericana",
        "copa sudamericana",
        "sudamericana",
        "recopa sudamericana",
        "conmebol recopa",
        "suruga bank",
    }

    # Selecciones argentinas
    TRUSTED_SELECTION_COMPETITIONS = {
        "fifa world cup",
        "world cup",
        "copa del mundo",
        "mundial",
        "eliminatorias",
        "eliminatorias conmebol",
        "world cup qualification",
        "fifa world cup qualification",
        "amistoso internacional",
        "international friendly",
        "friendly international",
        "copa america",
        "copa américa",
        "sudamericano sub 20",
        "sudamericano sub 17",
        "sudamericano sub 23",
        "preolimpico",
        "preolímpico",
        "juegos olimpicos",
        "juegos olímpicos",
        "olympic games",
        "conmebol nations league women",
        "nations league women",
        "fifa womens world cup",
        "fifa women's world cup",
        "mundial femenino",
    }

    # Ruido que no queremos priorizar por ahora
    NOISE_COMPETITION_KEYWORDS = {
        "reserve league international",
        "club friendly",
        "amistoso de clubes",
        "training match",
        "exhibition",
    }

    ARGENTINA_SELECTION_ALIASES = {
        "argentina",
        "argentina women",
        "argentina femenino",
        "argentina femenina",
        "argentina sub 17",
        "argentina sub 20",
        "argentina sub 23",
        "argentina u17",
        "argentina u20",
        "argentina u23",
        "seleccion argentina",
        "selección argentina",
        "argentina olimpica",
        "argentina olímpica",
    }

    # Alias exactos / controlados
    ARGENTINE_CLUB_ALIASES = {
        "aldosivi": {"aldosivi", "club atletico aldosivi"},
        "argentinos_juniors": {"argentinos juniors", "aa argentinos juniors"},
        "arsenal_sarandi": {"arsenal de sarandi", "arsenal sarandi"},
        "atletico_tucuman": {"atletico tucuman", "club atletico tucuman"},
        "banfield": {"banfield", "club atletico banfield"},
        "barracas_central": {"barracas central", "club atletico barracas central"},
        "belgrano": {"belgrano", "club atletico belgrano", "belgrano de cordoba"},
        "boca_juniors": {"boca juniors", "club atletico boca juniors"},
        "central_cordoba": {
            "central cordoba",
            "central cordoba sde",
            "central cordoba santiago del estero",
            "central cordoba de santiago",
        },
        "colon": {"colon", "colon de santa fe", "club atletico colon"},
        "defensa_y_justicia": {"defensa y justicia", "club defensa y justicia"},
        "deportivo_riestra": {"deportivo riestra", "riestra", "club deportivo riestra"},
        "estudiantes_lp": {"estudiantes", "estudiantes de la plata", "club estudiantes de la plata"},
        "ferro": {"ferro", "ferro carril oeste", "club ferro carril oeste"},
        "gimnasia_lp": {"gimnasia", "gimnasia y esgrima la plata", "gelp"},
        "godoy_cruz": {"godoy cruz", "godoy cruz antonio tomba"},
        "huracan": {"huracan", "club atletico huracan"},
        "independiente": {"independiente", "club atletico independiente"},
        "independiente_rivadavia": {"independiente rivadavia", "ind rivadavia", "cs independiente rivadavia"},
        "instituto": {"instituto", "instituto de cordoba", "instituto acc"},
        "lanus": {"lanus", "club atletico lanus"},
        "newells": {"newells", "newells old boys", "newell's old boys"},
        "platense": {"platense", "club atletico platense"},
        "quilmes": {"quilmes", "quilmes atletico club"},
        "racing": {"racing", "racing club", "racing club avellaneda"},
        "river": {"river plate", "club atletico river plate"},
        "rosario_central": {"rosario central", "club atletico rosario central"},
        "san_lorenzo": {"san lorenzo", "san lorenzo de almagro", "club atletico san lorenzo"},
        "san_martin_sj": {"san martin de san juan", "san martin san juan"},
        "san_martin_t": {"san martin de tucuman", "san martin tucuman"},
        "sarmiento": {"sarmiento", "sarmiento junin", "sarmiento de junin"},
        "talleres": {"talleres", "talleres de cordoba", "ca talleres"},
        "tigre": {"tigre", "club atletico tigre"},
        "union_sf": {"union de santa fe", "union santa fe", "club atletico union de santa fe"},
        "velez": {"velez", "velez sarsfield", "club atletico velez sarsfield"},
        # Ascenso / locales clave
        "all_boys": {"all boys"},
        "almagro": {"almagro"},
        "almirante_brown": {"almirante brown"},
        "agropecuario": {"agropecuario"},
        "atlanta": {"atlanta"},
        "brown_adrogue": {"brown de adrogue"},
        "chacarita": {"chacarita", "chacarita juniors"},
        "chaco_for_ever": {"chaco for ever"},
        "colon_sf": {"colon de santa fe"},
        "defensores_belgrano": {"defensores de belgrano"},
        "deportivo_madryn": {"deportivo madryn"},
        "deportivo_maipu": {"deportivo maipu", "deportivo maipú"},
        "deportivo_moron": {"deportivo moron", "deportivo morón"},
        "estudiantes_rc": {"estudiantes de rio cuarto", "estudiantes de río cuarto"},
        "gimnasia_mendoza": {"gimnasia de mendoza", "gimnasia y esgrima de mendoza"},
        "gimnasia_jujuy": {"gimnasia de jujuy"},
        "los_andes": {"los andes"},
        "mitre": {"mitre", "mitre de santiago del estero"},
        "nueva_chicago": {"nueva chicago"},
        "patronato": {"patronato"},
        "quilmes_ac": {"quilmes atletico club", "quilmes"},
        "san_miguel": {"san miguel"},
        "temperley": {"temperley"},
        "tristan_suarez": {"tristan suarez", "tristán suárez"},
        "union_mar_del_plata": {"union de mar del plata"},
    }

    def _norm(self, value: str | None) -> str:
        return normalize_str(value or "").replace("_", " ").strip()

    def _contains_noise(self, competition: str) -> bool:
        comp = self._norm(competition)
        return any(k in comp for k in self.NOISE_COMPETITION_KEYWORDS)

    def _is_trusted_local_competition(self, competition: str) -> bool:
        comp = self._norm(competition)
        return any(k in comp for k in self.TRUSTED_LOCAL_COMPETITIONS)

    def _is_trusted_international_competition(self, competition: str) -> bool:
        comp = self._norm(competition)
        return any(k in comp for k in self.TRUSTED_INTL_COMPETITIONS)

    def _is_trusted_selection_competition(self, competition: str) -> bool:
        comp = self._norm(competition)
        return any(k in comp for k in self.TRUSTED_SELECTION_COMPETITIONS)

    def _is_argentina_selection(self, name: str) -> bool:
        n = self._norm(name)
        return n in self.ARGENTINA_SELECTION_ALIASES or n.startswith("argentina ")

    def _resolve_argentine_club(self, name: str) -> str | None:
        n = self._norm(name)
        if not n:
            return None

        for canonical, aliases in self.ARGENTINE_CLUB_ALIASES.items():
            if n in aliases:
                return canonical

        # fallback flexible controlado
        for canonical, aliases in self.ARGENTINE_CLUB_ALIASES.items():
            for alias in aliases:
                if alias and alias in n:
                    return canonical

        return None

    def _classify_match(
        self,
        home: str,
        away: str,
        competition: str,
    ) -> tuple[str, str | None]:
        """
        Retorna:
        - ("seleccion", "Argentina")
        - ("club_arg", "<club>")
        - ("none", None)
        """

        home_norm = self._norm(home)
        away_norm = self._norm(away)
        comp_norm = self._norm(competition)

        if not home_norm or not away_norm:
            return "none", None

        if self._contains_noise(comp_norm):
            return "none", None

        # 1) Selección argentina
        if self._is_argentina_selection(home) or self._is_argentina_selection(away):
            return "seleccion", "Argentina"

        # 2) Clubes argentinos
        home_arg = self._resolve_argentine_club(home)
        away_arg = self._resolve_argentine_club(away)

        if home_arg or away_arg:
            # Ligas locales
            if self._is_trusted_local_competition(comp_norm):
                return "club_arg", home if home_arg else away

            # Copas internacionales
            if self._is_trusted_international_competition(comp_norm):
                return "club_arg", home if home_arg else away

            # Si la fuente vino rara pero detectamos club argentino real, igual entra
            return "club_arg", home if home_arg else away

        # 3) Fallback de selección
        if "argentina" in home_norm or "argentina" in away_norm:
            return "seleccion", "Argentina"

        return "none", None

    def _build_match(
        self,
        *,
        mid: str,
        source: str,
        competition: str,
        home: str,
        away: str,
        home_score,
        away_score,
        status: str,
        minute: str | None,
        start_time_arg: str | None,
        broadcast: str | None,
        raw: dict,
    ) -> NormalizedMatch | None:
        relevance, argentina_team = self._classify_match(home, away, competition)
        if relevance == "none":
            return None

        return NormalizedMatch(
            id=mid,
            sport="futbol",
            source=source,
            competition=competition or "Fútbol",
            home_team=home,
            away_team=away,
            home_score=home_score,
            away_score=away_score,
            status=status or "upcoming",
            minute=minute,
            start_time_arg=start_time_arg,
            argentina_relevance=relevance,
            argentina_team=argentina_team,
            broadcast=broadcast,
            raw=raw,
        )

    def _is_editorial_match(self, m: NormalizedMatch) -> bool:
        comp = self._norm(m.competition or "")
        rel = m.argentina_relevance or "none"

        if rel == "seleccion":
            return self._is_argentina_selection(m.home_team or "") or self._is_argentina_selection(m.away_team or "")

        if rel == "club_arg":
            if self._contains_noise(comp):
                return False
            # ahora dejamos pasar más, porque el filtro principal ya está en _classify_match
            return True

        return False

    async def scrape(self) -> list[NormalizedMatch]:
        matches: list[NormalizedMatch] = []
        seen: set[str] = set()
        diagnostics = {
            "diag_version": self.DIAG_VERSION,
            "sources": {},
            "total_unique": 0,
        }

        def add(m: NormalizedMatch | None):
            if not m:
                return
            if not self._is_editorial_match(m):
                return
            if m.id in seen:
                return
            seen.add(m.id)
            matches.append(m)

        def record(source: str, raw_count: int = 0, added_count: int = 0, error: str | None = None):
            diagnostics["sources"][source] = {
                "raw_count": raw_count,
                "added_count": added_count,
                "error": error,
            }

        # 1) Promiedos
        try:
            html = await get_today_html()
            raw = parse_matches(html)
            before = len(matches)

            for m in normalize_promiedos(raw):
                add(m)

            added = len(matches) - before
            record("promiedos", raw_count=len(raw), added_count=added)
            logger.info(f"[football/promiedos] +{added} ({len(raw)} raw)")
        except Exception as e:
            record("promiedos", error=str(e))
            logger.warning(f"[football/promiedos] {e}")

        # 2) AFA oficial
        try:
            html = await get_fixture_html()
            raw = parse_afa_fixture(html or "")
            before = len(matches)

            for m in normalize_promiedos(raw):
                add(m)

            added = len(matches) - before
            record("afa", raw_count=len(raw), added_count=added)
            logger.info(f"[football/afa] +{added} ({len(raw)} raw)")
        except Exception as e:
            record("afa", error=str(e))
            logger.warning(f"[football/afa] {e}")

        # 3) API-Football
        try:
            raw = await get_fixtures_today()
            before = len(matches)

            for f in raw:
                parsed = parse_api_football(f)
                if not parsed:
                    continue

                home = parsed.get("home", "") or ""
                away = parsed.get("away", "") or ""
                competition = parsed.get("competition", "") or ""

                item = self._build_match(
                    mid=f"futbol-api-football-{normalize_str(home)[:20]}-{normalize_str(away)[:20]}",
                    source="api_football",
                    competition=competition,
                    home=home,
                    away=away,
                    home_score=parsed.get("home_score"),
                    away_score=parsed.get("away_score"),
                    status=parsed.get("status", "upcoming"),
                    minute=parsed.get("minute"),
                    start_time_arg=parsed.get("start_time"),
                    broadcast=parsed.get("broadcast"),
                    raw=parsed,
                )
                add(item)

            added = len(matches) - before
            record("api_football", raw_count=len(raw), added_count=added)
            logger.info(f"[football/api_football] +{added} ({len(raw)} raw)")
        except Exception as e:
            record("api_football", error=str(e))
            logger.warning(f"[football/api_football] {e}")

        # 4) Sofascore
        try:
            before = len(matches)
            raw_total = 0

            for fn in [get_events_by_date, get_live_events]:
                data = await fn("futbol")
                events = data.get("events", [])
                raw_total += len(events)

                for m in sofascore_normalizer.normalize_events(events, "futbol"):
                    add(m)

            added = len(matches) - before
            record("sofascore", raw_count=raw_total, added_count=added)
            logger.info(f"[football/sofascore] +{added} ({raw_total} raw)")
        except Exception as e:
            record("sofascore", error=str(e))
            logger.warning(f"[football/sofascore] {e}")

        # 5) ESPN fallback final
        try:
            before = len(matches)
            espn_raw = await self._fetch_espn_events()

            for ev in espn_raw:
                nm = self._normalize_espn(ev)
                add(nm)

            added = len(matches) - before
            record("espn", raw_count=len(espn_raw), added_count=added)
            logger.info(f"[football/espn] +{added} ({len(espn_raw)} raw)")
        except Exception as e:
            record("espn", error=str(e))
            logger.warning(f"[football/espn] {e}")

        diagnostics["total_unique"] = len(matches)
        FootballAdapter.LAST_RUN = diagnostics
        logger.info(f"[football] TOTAL={len(matches)}")
        return matches

    async def _fetch_espn_events(self) -> list[dict]:
        date_yyyymmdd = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")).strftime("%Y%m%d")
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard?dates={date_yyyymmdd}"

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(12.0, connect=6.0),
            follow_redirects=True,
        ) as client:
            r = await client.get(url, headers={"User-Agent": "tablon-scraper/1.0"})
            r.raise_for_status()
            data = r.json()
            return data.get("events", [])

    def _normalize_espn(self, ev: dict) -> NormalizedMatch | None:
        comp_data = (ev.get("competitions") or [{}])[0]
        comp = comp_data.get("competition", {}).get("name", "Fútbol")

        competitors = comp_data.get("competitors", [])
        if len(competitors) < 2:
            return None

        home_obj = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
        away_obj = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])

        home = home_obj.get("team", {}).get("displayName", "")
        away = away_obj.get("team", {}).get("displayName", "")
        if not home or not away:
            return None

        status_type = ((comp_data.get("status") or {}).get("type") or {})
        state = status_type.get("state", "pre")
        detail = (status_type.get("shortDetail") or "").strip()

        if state == "in":
            status = "live"
        elif state == "post":
            status = "finished"
        else:
            status = "upcoming"

        def parse_score(c: dict):
            s = c.get("score")
            try:
                return int(s) if s not in (None, "") else None
            except Exception:
                return None

        minute = detail if status == "live" else None
        eid = ev.get("id") or f"{normalize_str(home)}-{normalize_str(away)}"

        return self._build_match(
            mid=f"futbol-espn-{eid}",
            source="espn",
            competition=comp,
            home=home,
            away=away,
            home_score=parse_score(home_obj),
            away_score=parse_score(away_obj),
            status=status,
            minute=minute,
            start_time_arg=None,
            broadcast=None,
            raw=ev,
        )
