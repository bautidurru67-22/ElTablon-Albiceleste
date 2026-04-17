"use client";

import { useEffect, useMemo, useState } from "react";
import styles from "./hoy.module.css";

type Match = {
  id: string;
  sport: string;
  competition: string;
  home_team: string;
  away_team: string;
  home_score?: number | null;
  away_score?: number | null;
  status: string;
  minute?: string | null;
  start_time?: string | null;
  tv?: string | null;
  category?: string;
  argentina_relevance?: string | null;
  argentina_team?: string | null;
  relevance_score?: number | null;
};

type Section = {
  key: string;
  title: string;
  items: Match[];
};

type HoyData = {
  date?: string;
  updated_at?: string;
  hero?: Match | null;
  matches: Match[];
  sections?: Section[];
};

const POLLING_MS = 15000;
const FETCH_TIMEOUT_MS = 12000;

export default function HoyPage() {
  const [data, setData] = useState<HoyData | null>(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    let cancelled = false;

    const fetchHoy = async () => {
      try {
        const payload = await fetchHoyPayload();
        const parsed = extractHoyData(payload);

        if (!cancelled) {
          setData(parsed);
          setError("");
        }
      } catch (err) {
        console.error("[hoy] fetch failed", err);
        if (!cancelled) {
          setError("No se pudo cargar la portada de hoy. Reintentamos automáticamente.");
          setData((prev) => prev || { matches: [], sections: [] });
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    fetchHoy();
    const pollId = window.setInterval(fetchHoy, POLLING_MS);
    const clockId = window.setInterval(() => setNow(Date.now()), 1000);

    return () => {
      cancelled = true;
      window.clearInterval(pollId);
      window.clearInterval(clockId);
    };
  }, []);

  const matches = data?.matches || [];
  const sections = useMemo(() => normalizeSections(data?.sections || [], matches), [data?.sections, matches]);
  const topEvent = data?.hero || matches[0] || null;

  if (isLoading && !data) {
    return (
      <main className={styles.page}>
        <div className={styles.wrapper}>
          <div className={styles.loading}>Cargando portada de hoy...</div>
        </div>
      </main>
    );
  }

  return (
    <main className={styles.page}>
      <div className={styles.wrapper}>
        {error ? <div className={styles.errorBox}>{error}</div> : null}

        <section className={styles.hero}>
          <div className={styles.heroMeta}>
            <span className={styles.metaChip}>PORTADA / HOY</span>
            <span className={styles.metaChip}>{formatDateEs(data?.date)}</span>
            <span className={styles.metaChip}>ACTUALIZADO {timeAgo(data?.updated_at, now)}</span>
          </div>

          {topEvent ? (
            <div className={styles.heroCard}>
              <div className={styles.heroBadges}>
                <StatusBadge status={normalizeStatus(topEvent.status)} />
                {getEditorialTags(topEvent).map((tag) => (
                  <span key={tag} className={styles.tag}>
                    {tag}
                  </span>
                ))}
                {topEvent.tv ? <span className={styles.tag}>TV: {topEvent.tv}</span> : null}
              </div>

              <div className={styles.heroEyebrow}>EVENTO DESTACADO</div>
              <h1 className={styles.heroTitle}>{participantLabel(topEvent)}</h1>
              <div className={styles.heroCompetition}>{topEvent.competition || "Agenda deportiva"}</div>

              <div className={styles.heroInfoRow}>
                {shouldShowScore(topEvent) ? (
                  <span className={styles.scorePill}>{formatScore(topEvent)}</span>
                ) : (
                  <span className={styles.scorePill}>{topEvent.start_time || "—"}</span>
                )}
              </div>
            </div>
          ) : (
            <div className={styles.emptyHero}>
              <div className={styles.emptyHeroTitle}>No hay eventos destacados por ahora.</div>
              <div className={styles.emptyHeroText}>
                En cuanto aparezca actividad relevante, la vas a ver acá arriba.
              </div>
            </div>
          )}
        </section>

        <section className={styles.columns}>
          {sections.map((section) => (
            <EventBlock key={section.key} title={section.title.toUpperCase()} matches={section.items} />
          ))}
        </section>
      </div>
    </main>
  );
}

function EventBlock({ title, matches }: { title: string; matches: Match[] }) {
  return (
    <article className={styles.block}>
      <div className={styles.blockHeader}>
        <h2 className={styles.blockTitle}>{title}</h2>
        <span className={styles.blockCount}>{matches.length}</span>
      </div>

      {matches.length === 0 ? (
        <div className={styles.blockEmpty}>Sin eventos</div>
      ) : (
        <div className={styles.cardList}>
          {matches.map((m) => (
            <div key={m.id} className={styles.matchCard}>
              <div className={styles.matchTitle}>{participantLabel(m)}</div>
              <div className={styles.matchCompetition}>{m.competition || "Agenda deportiva"}</div>
              <div className={styles.matchFooter}>
                <span className={styles.matchTime}>{m.start_time || "—"}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </article>
  );
}

function StatusBadge({ status }: { status: "live" | "upcoming" | "finished" }) {
  const label =
    status === "live" ? "EN VIVO" : status === "upcoming" ? "UPCOMING" : "FINALIZADO";

  return <span className={`${styles.statusBadge} ${styles[`statusBadge_${status}`]}`}>{label}</span>;
}

function normalizeSections(rawSections: Section[], matches: Match[]): Section[] {
  if (rawSections && rawSections.length > 0) {
    return rawSections.map((section) => ({
      ...section,
      items: section.items || [],
    }));
  }

  return [
    {
      key: "selecciones",
      title: "Selecciones nacionales",
      items: matches.filter((m) => m.category === "selecciones"),
    },
    {
      key: "ligas_locales",
      title: "Ligas locales",
      items: matches.filter((m) => m.category === "ligas_locales"),
    },
    {
      key: "exterior",
      title: "Argentinos en el exterior",
      items: matches.filter((m) => m.category === "exterior"),
    },
    {
      key: "motorsport",
      title: "Motorsport argentino",
      items: matches.filter((m) => m.category === "motorsport"),
    },
  ];
}

function normalizeStatus(status: string) {
  const normalized = (status || "").toLowerCase();

  if (["live", "en_vivo", "in_progress", "playing"].includes(normalized)) return "live";
  if (["upcoming", "scheduled", "programado", "pending", "not_started", "proximos"].includes(normalized)) return "upcoming";
  if (["finished", "finalizado", "ended", "ft", "completed", "finalizados"].includes(normalized)) return "finished";

  return "upcoming";
}

function getEditorialTags(match: Match) {
  const tags: string[] = [];
  const pool = [
    match.competition,
    match.category,
    match.argentina_team,
    match.argentina_relevance,
    match.home_team,
    match.away_team,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

  if (
    match.argentina_relevance === "seleccion" ||
    pool.includes("argentina u17") ||
    pool.includes("selección argentina") ||
    pool.includes("seleccion argentina")
  ) {
    tags.push("Selección");
  }

  if (match.argentina_relevance === "club_arg" || match.category === "ligas_locales") {
    tags.push("Liga local");
  }

  if (match.argentina_relevance === "jugador_arg" && !pool.includes("formula 1") && !pool.includes("motorsport")) {
    tags.push("Exterior");
  }

  if (pool.includes("motorsport") || pool.includes("formula 1") || pool.includes("motogp")) {
    tags.push("Motorsport");
  }

  if (tags.length === 0) {
    tags.push("Evento");
  }

  return tags.slice(0, 2);
}

function participantLabel(match: Match) {
  if (!match.away_team) return match.home_team;
  return `${match.home_team} vs ${match.away_team}`;
}

function shouldShowScore(match: Match) {
  const hasScore =
    match.home_score !== null &&
    match.home_score !== undefined &&
    match.away_score !== null &&
    match.away_score !== undefined;

  if (!hasScore) return false;

  const isSyntheticZeroZero =
    normalizeStatus(match.status) !== "live" &&
    Number(match.home_score) === 0 &&
    Number(match.away_score) === 0;

  return !isSyntheticZeroZero;
}

function formatScore(match: Match) {
  return `${match.home_score} - ${match.away_score}`;
}

function timeAgo(updatedAt: string | undefined, now: number) {
  if (!updatedAt) return "hace instantes";

  const timestamp = new Date(updatedAt).getTime();
  if (!Number.isFinite(timestamp)) return "hace instantes";

  const diffSeconds = Math.max(0, Math.floor((now - timestamp) / 1000));
  if (diffSeconds < 60) return `${diffSeconds}s`;

  const diffMinutes = Math.floor(diffSeconds / 60);
  if (diffMinutes < 60) return `${diffMinutes}s`;

  const diffHours = Math.floor(diffMinutes / 60);
  return `${diffHours}h`;
}

function formatDateEs(dateStr: string | undefined) {
  if (!dateStr) return "Fecha no disponible";

  try {
    return new Date(`${dateStr}T12:00:00`).toLocaleDateString("es-AR");
  } catch {
    return dateStr;
  }
}

function extractHoyData(json: unknown): HoyData {
  const root = toRecord(json);
  const directData = toRecord(root.data);

  return {
    date: pickString(directData.date, root.date),
    updated_at: pickString(directData.updated_at, root.updated_at),
    hero: toMatchOrNull(directData.hero),
    matches: toMatchArray(directData.matches),
    sections: toSections(directData.sections),
  };
}

function toSections(raw: unknown): Section[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .map((section) => {
      const record = toRecord(section);
      return {
        key: pickString(record.key) || "section",
        title: pickString(record.title) || "Sección",
        items: toMatchArray(record.items),
      };
    })
    .filter((section) => section.items.length > 0 || section.key);
}

function toMatchArray(raw: unknown): Match[] {
  return toRecordArray(raw)
    .map((item) => toMatch(item))
    .filter((match): match is Match => Boolean(match));
}

function toMatchOrNull(raw: unknown): Match | null {
  const record = toRecord(raw);
  return toMatch(record);
}

function toMatch(raw: Record<string, unknown>): Match | null {
  const homeTeam = pickString(raw.home_team, raw.homeTeam, raw.local, raw.home, raw.participant, raw.player) || "";
  const awayTeam = pickString(raw.away_team, raw.awayTeam, raw.visitante, raw.away, raw.rival, raw.opponent) || "";

  if (!homeTeam) return null;

  return {
    id: pickString(raw.id, raw.match_id, raw.matchId, raw.slug) || `${homeTeam}-${awayTeam || "evento"}`,
    sport: pickString(raw.sport, raw.deporte, raw.discipline) || "",
    competition: pickString(raw.competition, raw.league, raw.torneo, raw.event) || "",
    home_team: homeTeam,
    away_team: awayTeam,
    home_score: toNullableNumber(raw.home_score ?? raw.homeScore ?? raw.score_home),
    away_score: toNullableNumber(raw.away_score ?? raw.awayScore ?? raw.score_away),
    status: pickString(raw.status, raw.state, raw.estado) || "upcoming",
    minute: pickString(raw.minute, raw.clock, raw.game_minute),
    start_time: pickString(raw.start_time, raw.startTime, raw.time),
    tv: pickString(raw.tv, raw.channel, raw.broadcast),
    category: pickString(raw.category, raw.tag, raw.segment, raw.section),
    argentina_relevance: pickString(raw.argentina_relevance, raw.argentinaRelevance),
    argentina_team: pickString(raw.argentina_team, raw.argentinaTeam),
    relevance_score: toNullableNumber(raw.relevance_score ?? raw.relevanceScore),
  };
}

function toRecord(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function toRecordArray(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value)
    ? (value.filter((item) => typeof item === "object" && item !== null && !Array.isArray(item)) as Record<string, unknown>[])
    : [];
}

function pickString(...values: unknown[]) {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) return value;
  }
  return undefined;
}

function toNullableNumber(value: unknown): number | null | undefined {
  if (value === null) return null;
  if (value === undefined || value === "") return undefined;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : undefined;
}

async function fetchHoyPayload(): Promise<unknown> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);

  try {
    const res = await fetch("/api/proxy/api/hoy", {
      cache: "no-store",
      signal: controller.signal,
    });

    const text = await res.text();
    const payload = safeJsonParse(text);

    if (!res.ok) {
      const detail =
        pickString(
          (payload as Record<string, unknown>)?.error,
          (payload as Record<string, unknown>)?.detail,
          (payload as Record<string, unknown>)?.message,
        ) || `HTTP ${res.status}`;
      throw new Error(detail);
    }

    return payload;
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      throw new Error("Timeout al consultar portada de hoy");
    }
    throw error;
  } finally {
    window.clearTimeout(timer);
  }
}

function safeJsonParse(text: string): unknown {
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    console.warn("[hoy] invalid JSON payload from proxy");
    return {};
  }
}
