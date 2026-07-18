"use client";

import { useCallback, useEffect, useState } from "react";
import type { EvBet } from "./types";
import { profitPerUnit } from "./format";

// Prototype bet tracking: persisted to localStorage so it works with no backend.
// When Supabase + auth are wired, this moves to the org-scoped tracked_bets table
// (RLS-protected) — see PRD F8. Tracking = logging a bet you placed yourself; the
// app never places bets.
const KEY = "edge.tracked.v1";

export type TrackedBet = Pick<
  EvBet,
  "id" | "sport_id" | "market" | "selection" | "book" | "price" | "ev" | "model_prob" | "novig_prob"
> & { stake: number; placed_at: string };

function read(): TrackedBet[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(window.localStorage.getItem(KEY) || "[]");
  } catch {
    return [];
  }
}

export function useTrackedBets() {
  const [tracked, setTracked] = useState<TrackedBet[]>([]);

  useEffect(() => setTracked(read()), []);

  const persist = useCallback((next: TrackedBet[]) => {
    setTracked(next);
    window.localStorage.setItem(KEY, JSON.stringify(next));
  }, []);

  const isTracked = useCallback(
    (id: string) => tracked.some((t) => t.id === id),
    [tracked]
  );

  const toggle = useCallback(
    (bet: EvBet, stake = 1) => {
      const next = isTracked(bet.id)
        ? tracked.filter((t) => t.id !== bet.id)
        : [
            ...tracked,
            {
              id: bet.id,
              sport_id: bet.sport_id,
              market: bet.market,
              selection: bet.selection,
              book: bet.book,
              price: bet.price,
              ev: bet.ev,
              model_prob: bet.model_prob,
              novig_prob: bet.novig_prob,
              stake,
              placed_at: new Date().toISOString(),
            },
          ];
      persist(next);
    },
    [tracked, isTracked, persist]
  );

  const remove = useCallback(
    (id: string) => persist(tracked.filter((t) => t.id !== id)),
    [tracked, persist]
  );

  const clear = useCallback(() => persist([]), [persist]);

  const totalStake = tracked.reduce((s, t) => s + t.stake, 0);
  const potentialProfit = tracked.reduce(
    (s, t) => s + t.stake * profitPerUnit(t.price),
    0
  );
  const avgEv = tracked.length
    ? tracked.reduce((s, t) => s + t.ev, 0) / tracked.length
    : 0;

  return { tracked, isTracked, toggle, remove, clear, totalStake, potentialProfit, avgEv };
}
