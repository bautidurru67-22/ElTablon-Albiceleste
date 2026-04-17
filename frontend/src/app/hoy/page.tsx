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

type HoyData = {
  date?: string;
  updated_at?: string;
  matches: Match[];
};

const POLLING_MS = 15000;
const FETCH_TIMEOUT_MS = 12000;
const BLOCK_LIMIT = 8;

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
          setData((prev) => prev || { matches: [] });
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

  const matches = data?.matches ?? [];
  const grouped = useMemo(() => groupMatches(matches), [matches]);
  const topEvent = useMemo(() => pickTopEvent(matches), [matches]);

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
            <span className={styles.metaChip}>Portada / Hoy</span>
            <span className={styles.metaChip}>{formatDateEs(data?.date)}</span>
            <span className={styles.metaChip}>Actualizado {timeAgo(data?.updated_at, now)}</span>
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

              <div className={styles.heroEyebrow}>Evento destacado</div>
              <h1 className={styles.heroTitle}>{participantLabel(topEvent)}</h1>
              <div className={styles.heroCompetition}>{topEvent.competition || "Agenda deportiva"}</div>

              <div className={styles.heroInfoRow}>
                {shouldShowScore(topEvent) ? (
                  <span className={styles.scorePill}>{formatScore(topEvent)}</span>
                ) : (
                  <span className={styles.scorePill}>{topEvent.category || "Evento"}</span>
                )}
                <span className={styles.heroSubstatus}>{renderSubStatus(topEvent)}</span>
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

        {matches.length === 0 ? (
          <section className={styles.emptyState}>
            <h2 className={styles.emptyStateTitle}>Agenda vacía por el momento</h2>
            <p className={styles.emptyStateText}>
              No encontramos eventos para mostrar hoy. Volvé en unos minutos: esta portada se actualiza automáticamente.
            </p>
          </section>
        ) : (
          <section className={styles.columns}>
            <EventBlock title="EN VIVO" tone="live" matches={grouped.live} />
            <EventBlock title="PRÓXIMOS" tone="upcoming" matches={grouped.upcoming} />
            <EventBlock title="FINALIZADOS" tone="finished" matches={grouped.finished} />
          </section>
        )}
      </div>
    </main>
  );
}

function EventBlock({
  title,
  tone,
  matches,
}: {
  title: string;
  tone: "live" | "upcoming" | "finished";
  matches: Match[];
}) {
  return (
    <article className={styles.block}>
      <div className={styles.blockHeader}>
        <h2 className={styles.blockTitle}>{title}</h2>
        <span className={styles.blockCount}>{matches.length}</span>
      </div>

      {matches.length === 0 ? (
        <div className={styles.blockEmpty}>Sin eventos en esta sección.</div>
      ) : (
        <div className={styles.cardList}>
          {matches.map((match) => (
            <MatchCard key={match.id} match={match} tone={tone} />
          ))}
        </div>
      )}
    </article>
  );
}

function MatchCard({
  match,
  tone,
}: {
  match: Match;
  tone: "live" | "upcoming" | "finished";
}) {
  const scoreVisible = shouldShowScore(match);
  const editorialTags = getEditorialTags(match);

  return (
    <div className={styles.matchCard}>
      <div className={styles.matchBadges}>
        <StatusBadge status={normalizeStatus(match.status)} />
        {editorialTags.map((tag) => (
          <span key={tag} className={`${styles.editorialBadge} ${styles[`editorialBadge_${tone}`]}`}>
            {tag}
          </span>
        ))}
        <span className={styles.sportBadge}>{sportLabel(match.sport)}</span>
      </div>

      <div className={styles.matchTitle}>{participantLabel(match)}</div>
      <div className={styles.matchCompetition}>{match.competition || "Agenda deportiva"}</div>

      <div className={styles.matchFooter}>
        <span className={styles.matchTime}>{renderSubStatus(match)}</span>
        {scoreVisible ? (
          <span className={styles.matchScore}>{formatScore(match)}</span>
        ) : (
          <span className={styles.matchMeta}>{nonScoreLabel(match)}</span>
        )}
      </div>

      {match.tv ? <div className={styles.matchTv}>TV: {match.tv}</div> : null}
    </div>
  );
}

function StatusBadge({ status }: { status: "live" | "upcoming" | "finished" }) {
  const label =
    status === "live" ? "EN VIVO" : status === "upcoming" ? "PRÓXIMO" : "FINALIZADO";

  return <span className={`${styles.statusBadge} ${styles[`statusBadge_${status}`]}`}>{label}</span>;
}

function groupMatches(matches: Match[]) {
  const sorted = sortByEditorialPriority(matches);

  return {
    live: capForBlock(sorted.filter((m) => normalizeStatus(m.status) === "live"), BLOCK_LIMIT),
    upcoming: capForBlock(sorted.filter((m) => normalizeStatus(m.status) === "upcoming"), BLOCK_LIMIT),
    finished: capForBlock(sorted.filter((m) => normalizeStatus(m.status) === "finished"), BLOCK_LIMIT),
  };
}

function capForBlock(matches: Match[], limit: number) {
  if (matches.length <= limit) return matches;
  return matches.slice(0, limit);
}

function normalizeStatus(status: string) {
  const normalized = (status || "").toLowerCase();

  if (["live", "en_vivo", "in_progress", "playing"].includes(normalized)) return "live";
  if (["upcoming", "scheduled", "programado", "pending", "not_started", "proximos"].includes(normalized)) return "upcoming";
  if (["finished", "finalizado", "ended", "ft", "completed", "finalizados"].includes(normalized)) return "finished";

  return "upcoming";
}

function pickTopEvent(matches: Match[]) {
  const ranked = [...matches].sort((a, b) => heroPriorityScore(b) - heroPriorityScore(a));
  return ranked[0] || null;
}

function sortByEditorialPriority(matches: Match[]) {
  return [...matches].sort((a, b) => {
    const statusCmp = statusPriority(normalizeStatus(a.status)) - statusPriority(normalizeStatus(b.status));
    if (statusCmp !== 0) return statusCmp;

    const relevanceCmp = relevanceScore(b) - relevanceScore(a);
    if (relevanceCmp !== 0) return relevanceCmp;

    return timeSortKey(a).localeCompare(timeSortKey(b));
  });
}

function statusPriority(status: "live" | "upcoming" | "finished") {
  if (status === "live") return 0;
  if (status === "upcoming") return 1;
  return 2;
}

function heroPriorityScore(match: Match) {
  const status = normalizeStatus(match.status);
  const statusBoost = status === "live" ? 8 : status === "upcoming" ? 4 : 0;
  return relevanceScore(match) + statusBoost;
}

function relevanceScore(match: Match) {
  const backendScore = Number(match.relevance_score);
  if (Number.isFinite(backendScore)) return backendScore;

  const sport = normalizeSport(match.sport);
  const pool = [
    match.competition,
    match.home_team,
    match.away_team,
    match.category,
    match.argentina_team,
    match.argentina_relevance,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

  let score = 10;

  if (pool.includes("argentina")) score += 20;
  if (match.argentina_relevance === "seleccion") score += 70;
  if (match.argentina_relevance === "club_arg") score += 50;
  if (match.argentina_relevance === "jugador_arg") score += 35;
  if (sport === "futbol") score += 30;
  if (normalizeStatus(match.status) === "live") score += 10;
  if (match.argentina_team) score += 10;
  if (isSessionEvent(match)) score -= 30;
  if (sport === "motorsport") score -= 18;

  return score;
}

function renderSubStatus(match: Match) {
  const status = normalizeStatus(match.status);
  const rawMinute = (match.minute || "").trim();

  if (status === "live") return rawMinute || "En vivo";
  if (status === "upcoming") return match.start_time || "Próximamente";
  return rawMinute || "Finalizado";
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

  if (match.argentina_relevance === "seleccion" || pool.includes("argentina")) tags.push("Selección Argentina");
  if (match.category === "ligas_locales" || pool.includes("liga") || pool.includes("copa argentina")) tags.push("Liga local");
  if (match.argentina_relevance === "jugador_arg") tags.push("Argentino en el exterior");
  if (tags.length === 0) tags.push("Evento destacado");

  return tags.slice(0, 2);
}

function participantLabel(match: Match) {
  if (isSessionEvent(match)) {
    return match.argentina_team || [match.home_team, match.away_team].filter(Boolean).join(" · ") || "Evento en seguimiento";
  }

  if (!match.away_team) return match.home_team;
  return `${match.home_team} vs ${match.away_team}`;
}

function shouldShowScore(match: Match) {
  if (isSessionEvent(match)) return false;

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

function isSessionEvent(match: Match) {
  const pool = [match.sport, match.competition, match.category, match.home_team, match.away_team]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

  const sessionKeywords = [
    "practice",
    "práctica",
    "qualy",
    "clasificación",
    "session",
    "stage",
    "heat",
    "training",
    "entrenamiento",
    "fp1",
    "fp2",
    "fp3",
    "sprint",
  ];

  if (sessionKeywords.some((k) => pool.includes(k))) return true;
  return ["motorsport", "motogp", "formula 1", "f1", "rally"].some((k) => pool.includes(k));
}

function nonScoreLabel(match: Match) {
  if (isSessionEvent(match)) {
    return match.category || match.argentina_team || "Sesión";
  }
  return "Sin marcador";
}

function formatScore(match: Match) {
  return `${match.home_score} - ${match.away_score}`;
}

function sportLabel(sport: string | undefined) {
  const normalized = normalizeSport(sport);
  if (normalized === "futbol") return "Fútbol";
  if (normalized === "basquet") return "Básquet";
  if (normalized === "tenis") return "Tenis";
  if (normalized === "rugby") return "Rugby";
  if (normalized === "hockey") return "Hockey";
  if (normalized === "motorsport") return "Motorsport";
  return sport || "Deporte";
}

function normalizeSport(sport: string | undefined) {
  return (sport || "").toLowerCase().trim();
}

function timeSortKey(match: Match) {
  return (match.start_time || "99:99").padStart(5, "0");
}

function timeAgo(updatedAt: string | undefined, now: number) {
  if (!updatedAt) return "hace instantes";

  const timestamp = new Date(updatedAt).getTime();
  if (!Number.isFinite(timestamp)) return "hace instantes";

  const diffSeconds = Math.max(0, Math.floor((now - timestamp) / 1000));
  if (diffSeconds < 60) return `hace ${diffSeconds}s`;

  const diffMinutes = Math.floor(diffSeconds / 60);
  if (diffMinutes < 60) return `hace ${diffMinutes}min`;

  const diffHours = Math.floor(diffMinutes / 60);
  return `hace ${diffHours}h`;
}

function formatDateEs(dateStr: string | undefined) {
  if (!dateStr) return "Fecha no disponible";

  try {
    return new Date(`${dateStr}T12:00:00`).toLocaleDateString("es-AR", {
      weekday: "long",
      day: "numeric",
      month: "long",
    });
  } catch {
    return dateStr;
  }
}

function extractHoyData(json: unknown): HoyData {
  const root = toRecord(json);
  const directData = toRecord(root.data);
  const nestedData = toRecord(directData.data);

  const candidates = [root, directData, nestedData];

  for (const container of candidates) {
    const directMatches = toMatchArray(container.matches);
    if (directMatches.length > 0) {
      return {
        matches: sortByEditorialPriority(directMatches),
        date: pickString(container.date, root.date, directData.date),
        updated_at: pickString(container.updated_at, root.updated_at, directData.updated_at),
      };
    }
  }

  return {
    matches: [],
    date: pickString(root.date, directData.date),
    updated_at: pickString(root.updated_at, directData.updated_at),
  };
}

function toMatchArray(raw: unknown): Match[] {
  return toRecordArray(raw)
    .map((item) => toMatch(item, "upcoming"))
    .filter((match): match is Match => Boolean(match));
}

function toMatch(raw: Record<string, unknown>, fallbackStatus: Match["status"]): Match | null {
  const homeTeam = pickString(raw.home_team, raw.homeTeam, raw.local, raw.home, raw.participant, raw.player) || "";
  const awayTeam = pickString(raw.away_team, raw.awayTeam, raw.visitante, raw.away, raw.rival, raw.opponent) || "";
  const rawData = toRecord(raw.raw);

  if (!homeTeam) return null;

  return {
    id: pickString(raw.id, raw.match_id, raw.matchId, raw.slug) || `${homeTeam}-${awayTeam || "evento"}`,
    sport: pickString(raw.sport, raw.deporte, raw.discipline) || "",
    competition: pickString(raw.competition, raw.league, raw.torneo, raw.event) || "",
    home_team: homeTeam,
    away_team: awayTeam,
    home_score: toNullableNumber(raw.home_score ?? raw.homeScore ?? raw.score_home),
    away_score: toNullableNumber(raw.away_score ?? raw.awayScore ?? raw.score_away),
    status: pickString(raw.status, raw.state, raw.estado) || fallbackStatus,
    minute: pickString(raw.minute, raw.clock, raw.game_minute, rawData.minute),
    start_time: pickString(raw.start_time, raw.startTime, raw.time, rawData.start_time),
    tv: pickString(raw.tv, raw.channel, raw.broadcast, rawData.broadcast),
    category: pickString(raw.category, raw.tag, raw.segment, raw.session),
    argentina_relevance: pickString(raw.argentina_relevance, raw.argentinaRelevance, rawData.argentina_relevance),
    argentina_team: pickString(raw.argentina_team, raw.argentinaTeam, rawData.argentina_team),
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
    if (typeof value === "string" && value.trim()) {
      return value;
    }
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
