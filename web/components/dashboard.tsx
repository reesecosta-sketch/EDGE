"use client";

import { useMemo, useState } from "react";
import { useEvBets, ALL_SAMPLE, type Filters } from "@/lib/useEvBets";
import { useTrackedBets } from "@/lib/useTrackedBets";
import { supabaseConfigured } from "@/lib/supabase";
import type { EvBet } from "@/lib/types";
import {
  fmtOdds, fmtPct, fmtEv, fmtKelly, profitPerUnit, sportMeta, marketLabel,
} from "@/lib/format";

/* ---------------- small presentational pieces ---------------- */

function EvBadge({ ev }: { ev: number }) {
  const hot = ev >= 0.2;
  // a11y: never rely on color alone — arrow + sign + label carry the meaning.
  return (
    <span
      className={`ev-pill tnum ${hot ? "hot" : ""}`}
      aria-label={`Positive expected value ${(ev * 100).toFixed(1)} percent`}
    >
      <span aria-hidden>▲</span>
      {fmtEv(ev)}
    </span>
  );
}

function EdgeMeter({ model, fair }: { model: number; fair: number | null }) {
  const m = Math.max(0, Math.min(1, model));
  const f = fair == null ? null : Math.max(0, Math.min(1, fair));
  return (
    <div className="min-w-[92px]">
      <div className="meter" title={`Model ${fmtPct(model)} vs fair ${fmtPct(fair)}`}>
        <i style={{ width: `${m * 100}%` }} />
        {f != null && <u style={{ left: `${f * 100}%` }} />}
      </div>
      <div className="mt-1 flex justify-between text-[10.5px] tnum" style={{ color: "var(--faint)" }}>
        <span style={{ color: "var(--pos)" }}>{fmtPct(model, 0)}</span>
        <span>fair {fmtPct(fair, 0)}</span>
      </div>
    </div>
  );
}

function Confidence({ level }: { level?: EvBet["confidence"] }) {
  const n = level === "High" ? 3 : level === "Medium" ? 2 : level === "Low" ? 1 : 0;
  return (
    <span className="inline-flex items-center gap-2" title={`Confidence: ${level ?? "—"}`}>
      <span className="dots" aria-hidden>
        {[0, 1, 2].map((i) => (
          <i key={i} className={i < n ? "on" : ""} />
        ))}
      </span>
      <span className="text-[11px]" style={{ color: "var(--muted)" }}>{level ?? "—"}</span>
    </span>
  );
}

function StatTile({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="glass glass-2 card-hover p-4">
      <div className="text-[11px] uppercase tracking-wider" style={{ color: "var(--faint)" }}>{label}</div>
      <div className="mt-1 text-2xl font-bold tnum gradient-text">{value}</div>
      {sub && <div className="text-[11.5px] mt-0.5" style={{ color: "var(--muted)" }}>{sub}</div>}
    </div>
  );
}

/* ---------------- main dashboard ---------------- */

export default function Dashboard() {
  const [filters, setFilters] = useState<Filters>({ sport: null, market: null, minEv: 0.05 });
  const [sheetOpen, setSheetOpen] = useState(false);
  const { data = [], isLoading, error } = useEvBets(filters);
  const tb = useTrackedBets();

  const sports = useMemo(
    () => Array.from(new Set(ALL_SAMPLE.map((b) => b.sport_id))),
    []
  );
  const markets = useMemo(() => Array.from(new Set(data.map((b) => b.market))), [data]);

  const stats = useMemo(() => {
    if (!data.length) return { count: 0, avg: 0, top: 0, sports: 0 };
    return {
      count: data.length,
      avg: data.reduce((s, b) => s + b.ev, 0) / data.length,
      top: Math.max(...data.map((b) => b.ev)),
      sports: new Set(data.map((b) => b.sport_id)).size,
    };
  }, [data]);

  return (
    <div className="mx-auto max-w-[1240px] px-4 sm:px-6 pb-24">
      {/* ---- header ---- */}
      <header className="flex flex-wrap items-center gap-4 py-6">
        <div className="flex items-center gap-3">
          <div
            className="grid place-items-center h-10 w-10 rounded-xl text-lg font-black"
            style={{ background: "linear-gradient(180deg,#6ee7b7,#34d399)", color: "#04120c" }}
            aria-hidden
          >
            E
          </div>
          <div>
            <div className="text-xl font-extrabold leading-none">
              <span className="gradient-text">EDGE</span>
            </div>
            <div className="text-[12px]" style={{ color: "var(--muted)" }}>
              Positive-EV finder · decision support
            </div>
          </div>
        </div>

        <div className="ml-auto flex items-center gap-2.5">
          <span className="chip live" style={{ paddingLeft: 10 }}>
            <span className="ml-1">{supabaseConfigured ? "Live" : "Sample"} · updated now</span>
          </span>
          <button className="btn" onClick={() => setSheetOpen(true)} aria-label="Open tracked bets">
            ★ Tracked <span className="tnum">({tb.tracked.length})</span>
          </button>
        </div>
      </header>

      {!supabaseConfigured && (
        <div
          className="glass mb-5 px-4 py-3 text-[13px]"
          style={{ borderColor: "rgba(251,191,36,0.3)", color: "#fcd34d", background: "rgba(251,191,36,0.06)" }}
        >
          Showing <b>illustrative sample data</b>. Set <code>NEXT_PUBLIC_SUPABASE_URL</code> and{" "}
          <code>NEXT_PUBLIC_SUPABASE_ANON_KEY</code> (in Netlify env or <code>.env</code>) to load live bets.
        </div>
      )}

      {/* ---- stat tiles ---- */}
      <section className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        <StatTile label="+EV Bets" value={String(stats.count)} sub="above your threshold" />
        <StatTile label="Avg Edge" value={fmtEv(stats.avg)} sub="expected value" />
        <StatTile label="Top Edge" value={fmtEv(stats.top)} sub="best on the board" />
        <StatTile label="Sports" value={String(stats.sports)} sub="markets covered" />
      </section>

      {/* ---- filters ---- */}
      <section className="glass p-3 mb-4 flex flex-wrap items-center gap-3">
        <div className="seg" role="group" aria-label="Filter by sport">
          <button data-active={filters.sport === null} onClick={() => setFilters((f) => ({ ...f, sport: null }))}>
            All
          </button>
          {sports.map((s) => (
            <button
              key={s}
              data-active={filters.sport === s}
              onClick={() => setFilters((f) => ({ ...f, sport: s }))}
            >
              {sportMeta(s).icon} {sportMeta(s).label}
            </button>
          ))}
        </div>

        <select
          className="btn"
          style={{ paddingRight: 28 }}
          value={filters.market ?? ""}
          onChange={(e) => setFilters((f) => ({ ...f, market: e.target.value || null }))}
          aria-label="Filter by market"
        >
          <option value="">All markets</option>
          {markets.map((m) => (
            <option key={m} value={m}>{marketLabel(m)}</option>
          ))}
        </select>

        <label className="ml-auto flex items-center gap-3 text-[13px]" style={{ color: "var(--muted)" }}>
          <span className="whitespace-nowrap">Min EV</span>
          <input
            type="range" min={0} max={0.25} step={0.005}
            value={filters.minEv}
            onChange={(e) => setFilters((f) => ({ ...f, minEv: Number(e.target.value) }))}
            style={{ accentColor: "var(--pos)" }}
            aria-label="Minimum expected value"
          />
          <span className="ev-pill tnum">{(filters.minEv * 100).toFixed(1)}%</span>
        </label>
      </section>

      {/* ---- board ---- */}
      {isLoading && <div className="glass p-10 text-center" style={{ color: "var(--muted)" }}>Loading board…</div>}
      {error && <div className="glass p-6" style={{ color: "var(--neg)" }}>Failed to load: {String(error)}</div>}

      {!isLoading && !error && (
        <div className="glass overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[13.5px] border-collapse">
              <thead>
                <tr style={{ color: "var(--faint)" }} className="text-[11px] uppercase tracking-wider">
                  <th className="py-3 px-4 font-semibold">#</th>
                  <th className="py-3 px-4 font-semibold">Bet</th>
                  <th className="py-3 px-4 font-semibold">Market</th>
                  <th className="py-3 px-4 font-semibold">Book</th>
                  <th className="py-3 px-4 font-semibold text-right">Odds</th>
                  <th className="py-3 px-4 font-semibold">Model vs Fair</th>
                  <th className="py-3 px-4 font-semibold text-right">EV</th>
                  <th className="py-3 px-4 font-semibold text-right">Kelly</th>
                  <th className="py-3 px-4 font-semibold">Why</th>
                  <th className="py-3 px-4 font-semibold text-right">Track</th>
                </tr>
              </thead>
              <tbody>
                {data.map((b, i) => (
                  <tr
                    key={b.id}
                    className="row-in"
                    style={{ borderTop: "1px solid var(--border)", animationDelay: `${Math.min(i, 12) * 22}ms` }}
                  >
                    <td className="py-3 px-4 tnum font-bold" style={{ color: "var(--faint)" }}>{i + 1}</td>
                    <td className="py-3 px-4">
                      <div className="font-semibold">{b.selection}</div>
                      <div className="mt-0.5 flex items-center gap-1.5 text-[11.5px]" style={{ color: "var(--muted)" }}>
                        <span className="chip" style={{ padding: "1px 7px" }}>
                          {sportMeta(b.sport_id).icon} {sportMeta(b.sport_id).label}
                        </span>
                        {b.event_name && <span className="truncate max-w-[180px]">{b.event_name}</span>}
                      </div>
                    </td>
                    <td className="py-3 px-4"><span className="chip">{marketLabel(b.market)}</span></td>
                    <td className="py-3 px-4 capitalize" style={{ color: "var(--muted)" }}>{b.book}</td>
                    <td className="py-3 px-4 text-right tnum font-semibold">{fmtOdds(b.price)}</td>
                    <td className="py-3 px-4"><EdgeMeter model={b.model_prob} fair={b.novig_prob} /></td>
                    <td className="py-3 px-4 text-right"><EvBadge ev={b.ev} /></td>
                    <td className="py-3 px-4 text-right tnum" style={{ color: "var(--muted)" }}>{fmtKelly(b.kelly_frac)}</td>
                    <td className="py-3 px-4">
                      <div className="max-w-[260px] text-[12px] leading-snug" style={{ color: "var(--muted)", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }} title={b.rationale ?? ""}>
                        {b.rationale ?? "—"}
                      </div>
                      <div className="mt-1"><Confidence level={b.confidence} /></div>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        className="track-btn"
                        data-on={tb.isTracked(b.id)}
                        onClick={() => tb.toggle(b)}
                        aria-pressed={tb.isTracked(b.id)}
                        aria-label={tb.isTracked(b.id) ? `Untrack ${b.selection}` : `Track ${b.selection}`}
                      >
                        {tb.isTracked(b.id) ? "★ Tracked" : "☆ Track"}
                      </button>
                    </td>
                  </tr>
                ))}
                {data.length === 0 && (
                  <tr>
                    <td colSpan={10} className="py-14 text-center" style={{ color: "var(--faint)" }}>
                      No bets clear your {(filters.minEv * 100).toFixed(1)}% EV threshold. Lower it to see more.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ---- responsible-use footer ---- */}
      <footer className="mt-8 text-center text-[12px] leading-relaxed" style={{ color: "var(--faint)" }}>
        <p>
          <b style={{ color: "var(--muted)" }}>Decision support, not betting or financial advice.</b> EDGE surfaces
          and explains positive-EV opportunities; it never places bets. You place and manage your own wagers.
        </p>
        <p className="mt-1">If gambling stops being fun, get help — call 1-800-GAMBLER. 21+.</p>
      </footer>

      {/* ---- tracked slide-over ---- */}
      {sheetOpen && (
        <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-label="Tracked bets">
          <div className="absolute inset-0" style={{ background: "rgba(2,4,10,0.6)", backdropFilter: "blur(2px)" }} onClick={() => setSheetOpen(false)} />
          <aside className="sheet absolute right-0 top-0 h-full w-full sm:w-[420px] glass flex flex-col" style={{ borderRadius: 0, borderLeft: "1px solid var(--border-2)" }}>
            <div className="flex items-center justify-between p-4" style={{ borderBottom: "1px solid var(--border)" }}>
              <div className="font-bold text-lg">Your Tracked Bets</div>
              <button className="btn" onClick={() => setSheetOpen(false)} aria-label="Close">✕</button>
            </div>

            <div className="grid grid-cols-3 gap-2 p-4">
              <StatTile label="Staked" value={`${tb.totalStake.toFixed(0)}u`} />
              <StatTile label="To Win" value={`+${tb.potentialProfit.toFixed(1)}u`} />
              <StatTile label="Avg EV" value={tb.tracked.length ? fmtEv(tb.avgEv) : "—"} />
            </div>

            <div className="flex-1 overflow-y-auto px-4 pb-4 space-y-2">
              {tb.tracked.length === 0 && (
                <div className="text-center py-12 text-[13px]" style={{ color: "var(--faint)" }}>
                  No tracked bets yet. Hit <b>☆ Track</b> on any row to log a bet you placed.
                </div>
              )}
              {tb.tracked.map((t) => (
                <div key={t.id} className="glass glass-2 p-3 flex items-center gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="font-semibold truncate">{t.selection}</div>
                    <div className="text-[11.5px]" style={{ color: "var(--muted)" }}>
                      {sportMeta(t.sport_id).icon} {marketLabel(t.market)} · {t.book} · <span className="tnum">{fmtOdds(t.price)}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="tnum text-[13px]" style={{ color: "var(--pos)" }}>
                      +{(t.stake * profitPerUnit(t.price)).toFixed(2)}u
                    </div>
                    <button className="text-[11px] mt-0.5" style={{ color: "var(--faint)" }} onClick={() => tb.remove(t.id)}>
                      remove
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {tb.tracked.length > 0 && (
              <div className="p-4" style={{ borderTop: "1px solid var(--border)" }}>
                <button className="btn w-full" onClick={tb.clear}>Clear all</button>
                <p className="mt-2 text-center text-[11px]" style={{ color: "var(--faint)" }}>
                  Stored locally in your browser (prototype). Syncs to your account once sign-in is enabled.
                </p>
              </div>
            )}
          </aside>
        </div>
      )}
    </div>
  );
}
