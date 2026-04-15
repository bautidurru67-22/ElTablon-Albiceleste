"use client";

import { useEffect, useMemo, useState } from "react";

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

const POLLING_MS = 15_000;
const SECOND_MS = 1_000;
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
        const res = await fetch("/api/proxy/api/hoy", { cache: "no-store" });
        const json = await res.json();

        if (!res.ok) {
          throw new Error("No se pudo cargar la portada de hoy");
        }

        const parsed = extractHoyData(json);

        if (!cancelled) {
          setData(parsed);
          setError("");
        }
      } catch {
        if (!cancelled) {
          setError("No se pudo cargar la portada de hoy");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    fetchHoy();
    const pollId = window.setInterval(fetchHoy, POLLING_MS);
    const tickId = window.setInterval(() => setNow(Date.now()), SECOND_MS);

    return () => {
      cancelled = true;
      window.clearInterval(pollId);
      window.clearInterval(tickId);
    };
  }, []);

  const matches = data?.matches ?? [];
  const grouped = useMemo(() => groupMatches(matches), [matches]);
  const topEvent = useMemo(() => pickTopEvent(matches), [matches]);

  if (isLoading && !data) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-10 text-sm text-zinc-300 sm:px-6 lg:px-8">
        Cargando portada de hoy...
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="rounded-2xl border border-red-500/40 bg-red-950/20 p-6 text-red-100">
          {error}
        </div>
      </div>
    );
  }

  return (
    <main className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
      <header className="rounded-3xl border border-sky-400/30 bg-gradient-to-br from-sky-500/20 via-blue-500/10 to-zinc-900 p-6 shadow-[0_0_60px_-30px_rgba(56,189,248,0.7)] sm:p-8">
        <div className="mb-4 flex flex-wrap items-center gap-2 text-xs uppercase tracking-wide text-sky-100/80">
          <span className="rounded-full bg-sky-400/20 px-3 py-1">Portada / Hoy</span>
          <span className="rounded-full bg-white/10 px-3 py-1">{formatDateEs(data?.date)}</span>
          <span className="rounded-full bg-white/10 px-3 py-1">Actualizado {timeAgo(data?.updated_at, now)}</span>
        </div>

        {topEvent ? <HeroEvent match={topEvent} /> : <EmptyHero />}
      </header>

      {matches.length === 0 ? (
        <EmptyState />
      ) : (
        <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <EventBlock title="EN VIVO" tone="live" matches={grouped.live} />
          <EventBlock title="PRÓXIMOS" tone="upcoming" matches={grouped.upcoming} />
          <EventBlock title="FINALIZADOS" tone="finished" matches={grouped.finished} />
        </section>
      )}
    </main>
  );
}

function HeroEvent({ match }: { match: Match }) {
  const status = normalizeStatus(match.status);
  const scoreVisible = shouldShowScore(match);
  const editorialTags = getEditorialTags(match);

  return (
    <div className="rounded-2xl border border-white/10 bg-black/20 p-5 backdrop-blur">
      <div className="mb-3 flex flex-wrap items-center gap-2 text-xs">
        <StatusBadge status={status} />
        {editorialTags.map((tag) => (
          <span key={tag} className="rounded-full border border-white/20 bg-white/10 px-2.5 py-1 text-zinc-100">
            {tag}
          </span>
        ))}
        {match.tv ? <span className="rounded-full bg-white/10 px-2.5 py-1 text-zinc-100">TV: {match.tv}</span> : null}
      </div>

      <p className="text-sm font-medium text-zinc-300">Evento destacado</p>
      <h1 className="mt-1 text-2xl font-semibold text-white sm:text-3xl">{participantLabel(match)}</h1>
      <p className="mt-1 text-sm text-zinc-300">{match.competition || "Agenda deportiva"}</p>

      <div className="mt-4 flex flex-wrap items-center gap-4 text-sm text-zinc-100">
        {scoreVisible ? (
          <span className="rounded-lg bg-white/10 px-3 py-1.5 font-semibold">{formatScore(match)}</span>
        ) : (
          <span className="rounded-lg bg-white/10 px-3 py-1.5 font-semibold">{match.category || "Evento"}</span>
        )}
        <span>{renderSubStatus(match)}</span>
      </div>
    </div>
  );
}

function EmptyHero() {
  return (
    <div className="rounded-2xl border border-dashed border-white/20 bg-black/20 p-6 text-zinc-200">
      <p className="text-lg font-semibold">No hay eventos destacados por ahora.</p>
      <p className="mt-1 text-sm text-zinc-300">En cuanto aparezca actividad relevante, la vas a ver acá arriba.</p>
    </div>
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
    <article className="rounded-2xl border border-white/10 bg-zinc-950/70 p-4 shadow-xl shadow-black/20">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold tracking-wide text-zinc-100">{title}</h2>
        <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs text-zinc-300">{matches.length}</span>
      </div>

      {matches.length === 0 ? (
        <div className="rounded-xl border border-dashed border-zinc-700 p-4 text-sm text-zinc-400">
          Sin eventos en esta sección.
        </div>
      ) : (
        <div className="space-y-3">
          {matches.map((match) => (
            <MatchCard key={match.id} match={match} tone={tone} />
          ))}
        </div>
      )}
    </article>
  );
}

function MatchCard({ match, tone }: { match: Match; tone: "live" | "upcoming" | "finished" }) {
  const scoreVisible = shouldShowScore(match);
  const editorialTags = getEditorialTags(match);

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/90 p-4 transition hover:border-sky-500/50 hover:bg-zinc-900">
      <div className="mb-2 flex flex-wrap items-center gap-2 text-xs">
        <StatusBadge status={normalizeStatus(match.status)} />
        {editorialTags.map((tag) => (
          <EditorialBadge key={tag} label={tag} tone={tone} />
        ))}
        <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-zinc-300">{sportLabel(match.sport)}</span>
      </div>

      <p className="text-sm font-semibold text-zinc-100">{participantLabel(match)}</p>
      <p className="mt-1 text-xs text-zinc-400">{match.competition || "Agenda deportiva"}</p>

      <div className="mt-3 flex items-center justify-between gap-2 text-sm">
        <span className="text-zinc-300">{renderSubStatus(match)}</span>
        {scoreVisible ? (
          <span className="font-semibold text-white">{formatScore(match)}</span>
        ) : (
          <span className="text-xs text-zinc-400">{nonScoreLabel(match)}</span>
        )}
      </div>

      {match.tv ? <p className="mt-2 text-xs text-sky-200">TV: {match.tv}</p> : null}
    </div>
  );
}

function EditorialBadge({ label, tone }: { label: string; tone: "live" | "upcoming" | "finished" }) {
  const toneClass =
    tone === "live"
      ? "bg-red-500/20 text-red-200 border-red-400/40"
      : tone === "upcoming"
        ? "bg-amber-500/20 text-amber-200 border-amber-400/40"
        : "bg-emerald-500/20 text-emerald-200 border-emerald-400/40";

  return <span className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${toneClass}`}>{label}</span>;
}

function StatusBadge({ status }: { status: "live" | "upcoming" | "finished" }) {
  const base = "rounded-full border px-2 py-0.5 text-[11px] font-semibold";
  if (status === "live") return <span className={`${base} border-red-400/50 bg-red-500/20 text-red-100`}>EN VIVO</span>;
  if (status === "upcoming") return <span className={`${base} border-amber-400/50 bg-amber-500/20 text-amber-100`}>PRÓXIMO</span>;
  return <span className={`${base} border-emerald-400/50 bg-emerald-500/20 text-emerald-100`}>FINALIZADO</span>;
}

function EmptyState() {
  return (
    <section className="rounded-3xl border border-dashed border-zinc-700 bg-zinc-950/70 p-10 text-center">
      <h2 className="text-xl font-semibold text-zinc-100">Agenda vacía por el momento</h2>
      <p className="mx-auto mt-2 max-w-xl text-sm text-zinc-400">
        No encontramos eventos para mostrar hoy. Volvé en unos minutos: esta portada se actualiza automáticamente.
      </p>
    </section>
  );
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

  const maxPerSport = Math.max(2, Math.floor(limit / 2));
  const sportCount = new Map<string, number>();
  const picked: Match[] = [];

  for (const match of matches) {
    if (picked.length === limit) break;
    const sportKey = normalizeSport(match.sport);
    const current = sportCount.get(sportKey) || 0;
    if (current >= maxPerSport) continue;
    picked.push(match);
    sportCount.set(sportKey, current + 1);
  }

  if (picked.length < limit) {
    for (const match of matches) {
      if (picked.length === limit) break;
      if (picked.some((m) => m.id === match.id)) continue;
      picked.push(match);
    }
  }

  return picked;
}

function normalizeStatus(status: string) {
  const normalized = (status || "").toLowerCase();
  if (["live", "en_vivo", "in_progress", "playing"].includes(normalized)) return "live";
  if (["upcoming", "scheduled", "programado", "pending", "not_started", "proximos"].includes(normalized)) return "upcoming";
  if (["finished", "finalizado", "ended", "ft", "completed", "finalizados"].includes(normalized)) return "finished";
  return "upcoming";
}

function pickTopEvent(matches: Match[]) {
  const sorted = sortByEditorialPriority(matches);
  const live = sorted.find((m) => normalizeStatus(m.status) === "live");
  if (live) return live;

  const upcoming = sorted.find((m) => normalizeStatus(m.status) === "upcoming");
  if (upcoming) return upcoming;

  return sorted.find((m) => normalizeStatus(m.status) === "finished") || null;
}

function sortByEditorialPriority(matches: Match[]) {
  return [...matches].sort((a, b) => {
    const statusCmp = statusPriority(normalizeStatus(a.status)) - statusPriority(normalizeStatus(b.status));
    if (statusCmp !== 0) return statusCmp;

    const scoreCmp = relevanceScore(b) - relevanceScore(a);
    if (scoreCmp !== 0) return scoreCmp;

    return timeSortKey(a).localeCompare(timeSortKey(b));
  });
}

function statusPriority(status: "live" | "upcoming" | "finished") {
  if (status === "live") return 0;
  if (status === "upcoming") return 1;
  return 2;
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

  if (pool.includes("selección argentina") || pool.includes("argentina")) score += 20;
  if (match.argentina_relevance === "seleccion") score += 40;
  if (match.argentina_relevance === "club_arg") score += 30;
  if (match.argentina_relevance === "jugador_arg") score += 24;

  if (sport === "futbol") score += 26;
  if (pool.includes("liga profesional") || pool.includes("copa argentina")) score += 28;
  if (pool.includes("libertadores") || pool.includes("sudamericana")) score += 24;
  if (pool.includes("premier league") || pool.includes("serie a") || pool.includes("la liga") || pool.includes("bundesliga")) score += 16;

  if (normalizeStatus(match.status) === "live") score += 12;
  if (match.argentina_team) score += 8;

  return score;
}

function renderSubStatus(match: Match) {
  const status = normalizeStatus(match.status);
  if (status === "live") return match.minute || "En vivo";
  if (status === "upcoming") return match.start_time || "Próximamente";
  return match.minute || "Finalizado";
}

function getEditorialTags(match: Match) {
  const tags: string[] = [];
  const pool = [match.competition, match.category, match.argentina_team, match.argentina_relevance, match.home_team, match.away_team]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

  if (match.argentina_relevance === "seleccion" || pool.includes("selección argentina")) tags.push("Selección Argentina");
  if (pool.includes("liga profesional") || pool.includes("copa de la liga")) tags.push("Liga Profesional");
  if (match.argentina_relevance === "jugador_arg" || pool.includes("argentino")) tags.push("Argentino en el exterior");
  if (tags.length === 0) tags.push("Evento destacado");

  return tags.slice(0, 2);
}

function participantLabel(match: Match) {
  if (isSessionEvent(match)) {
    const participant = match.argentina_team || [match.home_team, match.away_team].filter(Boolean).join(" · ");
    return participant || "Evento en seguimiento";
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

  const sessionKeywords = ["practice", "práctica", "qualy", "clasificación", "session", "stage", "heat", "training", "entrenamiento", "fp1", "fp2", "fp3", "sprint"];
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
  // Shapes soportados (proxy/backend):
  // - json.data.matches
  // - json.matches
  // - json.data.data.matches
  // - json.{en_vivo, proximos, finalizados} (o dentro de data/data)
  const containers = collectCandidateContainers(json);

  for (const container of containers) {
    const directMatches = toMatchArray(container.matches);
    if (directMatches.length > 0) {
      return {
        matches: sortByEditorialPriority(directMatches),
        date: pickString(container.date, container.day, container.today),
        updated_at: pickString(container.updated_at, container.updatedAt, container.last_update),
      };
    }

    const fromSections = flattenSectionMatches(container);
    if (fromSections.length > 0) {
      return {
        matches: sortByEditorialPriority(fromSections),
        date: pickString(container.date, container.day, container.today),
        updated_at: pickString(container.updated_at, container.updatedAt, container.last_update),
      };
    }
  }

  return { matches: [] };
}

function collectCandidateContainers(raw: unknown): Array<Record<string, unknown>> {
  const root = toRecord(raw);
  const data = toRecord(root.data);
  const nestedData = toRecord(data.data);
  const payload = toRecord(root.payload);
  const result = toRecord(root.result);

  return [root, data, nestedData, payload, result].filter((x) => Object.keys(x).length > 0);
}

function flattenSectionMatches(container: Record<string, unknown>) {
  const sections: Array<{ key: string; status: Match["status"] }> = [
    { key: "en_vivo", status: "live" },
    { key: "live", status: "live" },
    { key: "proximos", status: "upcoming" },
    { key: "upcoming", status: "upcoming" },
    { key: "finalizados", status: "finished" },
    { key: "finished", status: "finished" },
  ];

  const flattened: Match[] = [];

  for (const section of sections) {
    const list = toRecordArray(container[section.key]);
    for (const item of list) {
      const match = toMatch(item, section.status);
      if (match) flattened.push(match);
    }
  }

  return flattened;
}

function toMatchArray(raw: unknown): Match[] {
  return toRecordArray(raw)
    .map((item) => toMatch(item, "upcoming"))
    .filter((match): match is Match => Boolean(match));
}

function toMatch(raw: Record<string, unknown>, fallbackStatus: Match["status"]): Match | null {
  const home_team = pickString(raw.home_team, raw.homeTeam, raw.local, raw.home, raw.participant, raw.player);
  const away_team = pickString(raw.away_team, raw.awayTeam, raw.visitante, raw.away, raw.rival, raw.opponent) || "";

  if (!home_team) {
    return null;
  }

  return {
    id: pickString(raw.id, raw.match_id, raw.matchId, raw.slug) || `${home_team}-${away_team || "evento"}`,
    sport: pickString(raw.sport, raw.deporte, raw.discipline) || "",
    competition: pickString(raw.competition, raw.league, raw.torneo, raw.event) || "",
    home_team,
    away_team,
    home_score: toNullableNumber(raw.home_score ?? raw.homeScore ?? raw.score_home),
    away_score: toNullableNumber(raw.away_score ?? raw.awayScore ?? raw.score_away),
    status: pickString(raw.status, raw.state, raw.estado) || fallbackStatus,
    minute: pickString(raw.minute, raw.clock, raw.game_minute),
    start_time: pickString(raw.start_time, raw.startTime, raw.time),
    tv: pickString(raw.tv, raw.channel, raw.broadcast),
    category: pickString(raw.category, raw.tag, raw.segment, raw.session),
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
