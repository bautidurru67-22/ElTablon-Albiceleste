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

export default function HoyPage() {
  const [data, setData] = useState<HoyData | null>(null);
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    const fetchHoy = async () => {
      const res = await fetch("/api/proxy/api/hoy", { cache: "no-store" });
      const json = await res.json();

      const matches = json?.data?.matches || [];

      setData({
        date: json?.date,
        updated_at: json?.data?.updated_at,
        matches,
      });
    };

    fetchHoy();
    const poll = setInterval(fetchHoy, POLLING_MS);
    const clock = setInterval(() => setNow(Date.now()), 1000);

    return () => {
      clearInterval(poll);
      clearInterval(clock);
    };
  }, []);

  const matches = data?.matches || [];

  const grouped = useMemo(() => groupMatchesByCategory(matches), [matches]);
  const topEvent = useMemo(() => pickTopEvent(matches), [matches]);

  return (
    <main className={styles.page}>
      <div className={styles.wrapper}>
        <section className={styles.hero}>
          <div className={styles.heroMeta}>
            <span className={styles.metaChip}>PORTADA / HOY</span>
            <span className={styles.metaChip}>{formatDate(data?.date)}</span>
            <span className={styles.metaChip}>
              ACTUALIZADO {timeAgo(data?.updated_at, now)}
            </span>
          </div>

          {topEvent && (
            <div className={styles.heroCard}>
              <div className={styles.heroBadges}>
                <StatusBadge status={topEvent.status} />
                {getEditorialTags(topEvent).map((tag) => (
                  <span key={tag} className={styles.tag}>
                    {tag}
                  </span>
                ))}
              </div>

              <div className={styles.heroEyebrow}>EVENTO DESTACADO</div>
              <h1 className={styles.heroTitle}>
                {participantLabel(topEvent)}
              </h1>
              <div className={styles.heroCompetition}>
                {topEvent.competition}
              </div>

              <div className={styles.heroInfoRow}>
                <span className={styles.scorePill}>
                  {topEvent.start_time || "—"}
                </span>
              </div>
            </div>
          )}
        </section>

        <section className={styles.columns}>
          <EventBlock
            title="SELECCIONES NACIONALES"
            matches={grouped.seleccion}
          />
          <EventBlock
            title="LIGAS LOCALES"
            matches={grouped.ligas}
          />
          <EventBlock
            title="ARGENTINOS EN EL EXTERIOR"
            matches={grouped.exterior}
          />
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
              <div className={styles.matchTitle}>
                {participantLabel(m)}
              </div>
              <div className={styles.matchCompetition}>
                {m.competition}
              </div>
              <div className={styles.matchFooter}>
                <span>{m.start_time || "—"}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </article>
  );
}

function groupMatchesByCategory(matches: Match[]) {
  return {
    seleccion: matches.filter((m) => m.argentina_relevance === "seleccion"),
    ligas: matches.filter(
      (m) =>
        m.argentina_relevance === "club_arg" ||
        m.category === "ligas_locales"
    ),
    exterior: matches.filter(
      (m) => m.argentina_relevance === "jugador_arg"
    ),
  };
}

function pickTopEvent(matches: Match[]) {
  return [...matches].sort((a, b) => relevanceScore(b) - relevanceScore(a))[0];
}

function relevanceScore(match: Match) {
  let score = 0;

  if (match.argentina_relevance === "seleccion") score += 100;
  if (match.argentina_relevance === "club_arg") score += 70;
  if (match.argentina_relevance === "jugador_arg") score += 40;

  if (match.sport === "futbol") score += 30;
  if (match.sport === "motorsport") score -= 20;

  if (match.status === "live") score += 50;

  return score;
}

function participantLabel(match: Match) {
  if (!match.away_team) return match.home_team;
  return `${match.home_team} vs ${match.away_team}`;
}

function getEditorialTags(match: Match) {
  if (match.argentina_relevance === "seleccion") return ["Selección"];
  if (match.argentina_relevance === "club_arg") return ["Liga local"];
  if (match.argentina_relevance === "jugador_arg") return ["Exterior"];
  return ["Evento"];
}

function StatusBadge({ status }: { status: string }) {
  return <span className={styles.statusBadge}>{status}</span>;
}

function formatDate(date?: string) {
  if (!date) return "";
  return new Date(date).toLocaleDateString("es-AR");
}

function timeAgo(date?: string, now?: number) {
  if (!date || !now) return "";
  const diff = Math.floor((now - new Date(date).getTime()) / 1000);
  if (diff < 60) return `${diff}s`;
  if (diff < 3600) return `${Math.floor(diff / 60)}min`;
  return `${Math.floor(diff / 3600)}h`;
}
