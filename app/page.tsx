"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import WATCHES from "../data/watches.json";

type Watch = { id: string; brand: string; model: string; ref: string; price: number; tier: number; img: string; source: string };
const ALL = WATCHES as Watch[];
const K = 32;
const START = 1500;
const LS_KEY = "wristrank-v1";
const ADVANCE_MS = 1500;

const TIER_NAMES: Record<number, string> = {
  1: "Tier 1 · Under $500",
  2: "Tier 2 · $500–2K",
  3: "Tier 3 · $2K–6K",
  4: "Tier 4 · $6K–15K",
  5: "Tier 5 · Grail $15K+",
};
const fmt = (n: number) => "$" + n.toLocaleString("en-US");

type State = {
  elo: Record<string, number>;
  wins: Record<string, number>;
  games: Record<string, number>;
  votes: number;
  list: string[];
};

function freshState(): State {
  return { elo: {}, wins: {}, games: {}, votes: 0, list: [] };
}
function eloOf(s: State, id: string) {
  return s.elo[id] ?? START;
}
function pickPair(): [Watch, Watch] {
  const a = ALL[Math.floor(Math.random() * ALL.length)];
  let b = ALL[Math.floor(Math.random() * ALL.length)];
  let guard = 0;
  const crossTier = Math.random() < 0.3;
  while (b.id === a.id || (!crossTier && Math.abs(b.tier - a.tier) > 1) || (crossTier && b.tier === a.tier)) {
    b = ALL[Math.floor(Math.random() * ALL.length)];
    if (++guard > 60) break;
  }
  if (b.id === a.id) b = ALL[(ALL.indexOf(a) + 7) % ALL.length];
  return [a, b];
}

export default function Home() {
  const [tab, setTab] = useState<"play" | "ranks" | "list">("play");
  const [s, setS] = useState<State>(freshState);
  const [loaded, setLoaded] = useState(false);
  const [pair, setPair] = useState<[Watch, Watch] | null>(null);
  const [picked, setPicked] = useState<string | null>(null);
  const [result, setResult] = useState<{ da: number; db: number } | null>(null);
  const [paused, setPaused] = useState(false);
  const [filter, setFilter] = useState(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(LS_KEY);
      if (raw) setS({ ...freshState(), ...JSON.parse(raw) });
    } catch {}
    setLoaded(true);
  }, []);
  useEffect(() => {
    if (loaded) localStorage.setItem(LS_KEY, JSON.stringify(s));
  }, [s, loaded]);
  useEffect(() => {
    if (loaded && !pair) setPair(pickPair());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loaded]);
  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);

  function clearTimer() {
    if (timer.current) { clearTimeout(timer.current); timer.current = null; }
  }

  function advance() {
    clearTimer();
    setPaused(false);
    setPair(pickPair());
    setPicked(null);
    setResult(null);
  }

  function vote(winner: Watch) {
    if (!pair || picked) return;
    const [a, b] = pair;
    const ra = eloOf(s, a.id), rb = eloOf(s, b.id);
    const ea = 1 / (1 + Math.pow(10, (rb - ra) / 400));
    const eb = 1 - ea;
    const na = Math.round(ra + K * ((winner.id === a.id ? 1 : 0) - ea));
    const nb = Math.round(rb + K * ((winner.id === b.id ? 1 : 0) - eb));
    setS({
      ...s,
      elo: { ...s.elo, [a.id]: na, [b.id]: nb },
      wins: { ...s.wins, [winner.id]: (s.wins[winner.id] ?? 0) + 1 },
      games: { ...s.games, [a.id]: (s.games[a.id] ?? 0) + 1, [b.id]: (s.games[b.id] ?? 0) + 1 },
      votes: s.votes + 1,
    });
    setPicked(winner.id);
    setResult({ da: na - ra, db: nb - rb });
    clearTimer();
    timer.current = setTimeout(advance, ADVANCE_MS);
  }

  function onCard(w: Watch) {
    if (picked) advance();
    else vote(w);
  }

  function onHeart(e: React.MouseEvent, id: string) {
    e.stopPropagation();
    toggleList(id);
    if (picked) { clearTimer(); setPaused(true); }
  }

  function goTab(t: "play" | "ranks" | "list") {
    clearTimer();
    setTab(t);
  }

  function toggleList(id: string) {
    setS((prev) => ({ ...prev, list: prev.list.includes(id) ? prev.list.filter((x) => x !== id) : [...prev.list, id] }));
  }

  const ranked = useMemo(
    () => [...ALL].sort((x, y) => eloOf(s, y.id) - eloOf(s, x.id) || (s.wins[y.id] ?? 0) - (s.wins[x.id] ?? 0)),
    [s]
  );
  const shownRanks = filter === 0 ? ranked : ranked.filter((w) => w.tier === filter);
  const listWatches = s.list.map((id) => ALL.find((w) => w.id === id)).filter(Boolean) as Watch[];
  const listTotal = listWatches.reduce((t, w) => t + w.price, 0);
  const winner = picked && pair ? pair.find((w) => w.id === picked)! : null;
  const loser = picked && pair ? pair.find((w) => w.id !== picked)! : null;
  const upset = !!(winner && loser && winner.tier > loser.tier);

  function Card({ w, side }: { w: Watch; side: number }) {
    const isPicked = picked === w.id;
    const revealed = !!picked;
    const delta = result ? (side === 0 ? result.da : result.db) : 0;
    const score = eloOf(s, w.id);
    const listed = s.list.includes(w.id);
    return (
      <div
        className={"card" + (revealed ? " revealed" : "") + (isPicked ? " picked" : revealed ? " beaten" : "")}
        onClick={() => onCard(w)}
        role="button"
        aria-label="Pick this watch"
      >
        <div className="ph"><img src={w.img} alt={revealed ? `${w.brand} ${w.model}` : "Mystery watch"} draggable={false} /></div>
        {isPicked && <div className="winner-flag">★ YOUR PICK</div>}
        {revealed && (
          <button className={"heart" + (listed ? " added" : "")} onClick={(e) => onHeart(e, w.id)} aria-label="Toggle on my list">
            {listed ? "♥" : "♡"}
          </button>
        )}
        {!revealed ? (
          <div className="mystery"><span className="q">? ? ?</span><span>TAP TO PICK</span></div>
        ) : (
          <div className="reveal">
            <div className="brand">{w.brand}</div>
            <div className="model">{w.model}</div>
            <div className="row">
              <span className="price">{fmt(w.price)}</span>
              <span className={"chip t" + w.tier}>{TIER_NAMES[w.tier].split("·")[0].trim()}</span>
              {w.ref ? <span className="ref">Ref. {w.ref}</span> : null}
              <span className="elo">
                <span className="score">{score}</span>{" "}
                <span className={"delta " + (delta >= 0 ? "up" : "down")}>{delta >= 0 ? "+" : ""}{delta}</span>
              </span>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={"wrap" + (tab === "play" ? " playing" : "")}>
      <header className="topbar">
        <div className="logo">WRIST<b>RANK</b></div>
        <div className="streak"><b>{s.votes}</b> votes · <b>{s.list.length}</b> listed</div>
      </header>

      {tab === "play" && (
        <div className="stage">
          {pair && (
            <div className="duel" key={pair[0].id + "|" + pair[1].id}>
              <Card w={pair[0]} side={0} />
              <div className="vs">VS</div>
              <Card w={pair[1]} side={1} />
              {picked && upset && <div className="upset">🔥 UPSET - cheaper tier takes it</div>}
            </div>
          )}
          <div className="stagefoot">
            {!picked ? (
              <button className="skip" onClick={advance}>skip this pair ⟳</button>
            ) : paused ? (
              <button className="nextmini" onClick={advance}>Next matchup ▸</button>
            ) : (
              <div className="autobar" key={pair ? pair[0].id + pair[1].id + picked : "x"}><i /></div>
            )}
          </div>
        </div>
      )}

      {tab === "ranks" && (
        <>
          <div className="h2">Leaderboard</div>
          <p className="sub">Your personal Elo rankings across {ALL.length} watches. Vote more to sharpen them.</p>
          <div className="filters">
            <button className={filter === 0 ? "on" : ""} onClick={() => setFilter(0)}>All tiers</button>
            {[1, 2, 3, 4, 5].map((t) => (
              <button key={t} className={filter === t ? "on" : ""} onClick={() => setFilter(t)}>{TIER_NAMES[t]}</button>
            ))}
          </div>
          {shownRanks.slice(0, 60).map((w, i) => (
            <div className="rank-row" key={w.id}>
              <div className="rk">{i + 1}</div>
              <img className="thumb" src={w.img} alt="" loading="lazy" />
              <div className="info">
                <div className="b">{w.brand}</div>
                <div className="m">{w.model}</div>
                <div className="p">{fmt(w.price)} · {TIER_NAMES[w.tier].split("·")[0].trim()}</div>
              </div>
              <div className="score">
                <div className="s">{eloOf(s, w.id)}</div>
                <div className="w">{s.wins[w.id] ?? 0}W · {s.games[w.id] ?? 0} played</div>
              </div>
              <button className={"mini-add" + (s.list.includes(w.id) ? " added" : "")} onClick={() => toggleList(w.id)} aria-label="Toggle on my list">
                {s.list.includes(w.id) ? "♥" : "♡"}
              </button>
            </div>
          ))}
          <p className="foot">
            Prices are median secondary-market prices computed from a 284K-listing Chrono24 dataset, cached at build time.
            Photos via dealer listings. Men&apos;s watches only. Elo starts at 1500, K = 32 - beat a higher-rated watch, gain more.
          </p>
        </>
      )}

      {tab === "list" && (
        <>
          <div className="h2">My watch list</div>
          <p className="sub">The ones you keep coming back to. Built from your votes.</p>
          {listWatches.length > 0 && (
            <div className="totalbar">
              <span className="t">{listWatches.length} watches</span>
              <span className="v">{fmt(listTotal)}</span>
            </div>
          )}
          {listWatches.length === 0 ? (
            <div className="empty">Nothing here yet.<br />Vote in a matchup, then tap the heart on any watch you love.</div>
          ) : (
            listWatches.map((w) => (
              <div className="rank-row" key={w.id}>
                <img className="thumb" src={w.img} alt="" loading="lazy" />
                <div className="info">
                  <div className="b">{w.brand}</div>
                  <div className="m">{w.model}</div>
                  <div className="p">{w.ref ? "Ref. " + w.ref + " · " : ""}{TIER_NAMES[w.tier]}</div>
                </div>
                <div className="score">
                  <div className="s">{fmt(w.price)}</div>
                  <div className="w">Elo {eloOf(s, w.id)}</div>
                </div>
                <button className="mini-add added" onClick={() => toggleList(w.id)} aria-label="Remove from my list">♥</button>
              </div>
            ))
          )}
          <p className="foot">
            Prices are median secondary-market prices computed from a 284K-listing Chrono24 dataset, cached at build time.
            Photos via dealer listings. Men&apos;s watches only.
          </p>
        </>
      )}

      <nav className="nav">
        <button className={tab === "play" ? "on" : ""} onClick={() => goTab("play")}>⚔️ Duel</button>
        <button className={tab === "ranks" ? "on" : ""} onClick={() => goTab("ranks")}>🏆 Ranks</button>
        <button className={tab === "list" ? "on" : ""} onClick={() => goTab("list")}>♥ My List</button>
      </nav>
    </div>
  );
}
