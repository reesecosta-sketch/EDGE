import { useQuery } from "@tanstack/react-query";
import { supabase, supabaseConfigured } from "./supabase";
import type { EvBet } from "./types";

export type Filters = { sport: string | null; market: string | null; minEv: number };

// Rich sample board so the prototype looks and works great with no backend.
// These are illustrative, NOT live recommendations. Once Supabase env vars are set
// the hook pulls real rows instead.
const now = new Date().toISOString();

// Quarter-Kelly, capped at 5% of bankroll — mirrors worker/core/devig.py.
function sampleKelly(price: number, p: number): number {
  const b = price > 0 ? price / 100 : 100 / -price;
  const full = (b * p - (1 - p)) / b;
  return full <= 0 ? 0 : Math.min(full * 0.25, 0.05);
}

const S = (o: Partial<EvBet> & Pick<EvBet, "id" | "sport_id" | "market" | "selection" | "book" | "price" | "model_prob" | "novig_prob" | "ev">): EvBet => ({
  event_id: "sample",
  kelly_frac: sampleKelly(o.price!, o.model_prob!),
  rationale: null,
  flagged_at: now,
  status: "open",
  trust_tier: "experimental",
  ...o,
});

const SAMPLE: EvBet[] = [
  S({ id: "g1", sport_id: "golf", event_name: "The Open Championship", market: "top_10", selection: "Ludvig Åberg", book: "pinnacle", price: 275, model_prob: 0.32, novig_prob: 0.243, ev: 0.198, confidence: "High", rationale: "Model gives Åberg a 32% top-10 chance vs. 24% fair — a +7.7pt edge, driven mainly by strokes-gained approach and links course fit." }),
  S({ id: "g2", sport_id: "golf", event_name: "The Open Championship", market: "make_cut", selection: "Tommy Fleetwood", book: "draftkings", price: -140, model_prob: 0.71, novig_prob: 0.612, ev: 0.156, confidence: "High", rationale: "71% make-cut vs. 61% fair — a +9.8pt edge from elite driving accuracy and strong recent form." }),
  S({ id: "g3", sport_id: "golf", event_name: "The Open Championship", market: "top_5", selection: "Viktor Hovland", book: "fanduel", price: 650, model_prob: 0.16, novig_prob: 0.121, ev: 0.174, confidence: "Medium", rationale: "16% top-5 vs. 12% fair — a +3.9pt edge; iron play and course history carry the projection." }),
  S({ id: "g4", sport_id: "golf", event_name: "The Open Championship", market: "make_cut", selection: "Robert MacIntyre", book: "betmgm", price: 120, model_prob: 0.55, novig_prob: 0.461, ev: 0.21, confidence: "Medium", rationale: "55% make-cut vs. 46% fair — a +8.9pt edge; home-nation links pedigree and putting uptick." }),
  S({ id: "g5", sport_id: "golf", event_name: "The Open Championship", market: "top_20", selection: "Matt Fitzpatrick", book: "pinnacle", price: 180, model_prob: 0.44, novig_prob: 0.368, ev: 0.232, confidence: "High", rationale: "44% top-20 vs. 37% fair — a +7.2pt edge from scrambling and wind-scoring history." }),
  S({ id: "g6", sport_id: "golf", event_name: "The Open Championship", market: "outright", selection: "Xander Schauffele", book: "caesars", price: 1400, model_prob: 0.09, novig_prob: 0.071, ev: 0.286, confidence: "Low", rationale: "9% to win vs. 7% fair — a +1.9pt edge; consistency and closing record priced softly." }),
  S({ id: "g7", sport_id: "golf", event_name: "Genesis Scottish Open", market: "top_10", selection: "Aaron Rai", book: "draftkings", price: 450, model_prob: 0.21, novig_prob: 0.171, ev: 0.155, confidence: "Medium", rationale: "21% top-10 vs. 17% fair — a +3.9pt edge; accuracy fits a demanding setup." }),
  S({ id: "n1", sport_id: "nascar", event_name: "Brickyard 400", market: "top_5", selection: "William Byron", book: "betmgm", price: 240, model_prob: 0.35, novig_prob: 0.28, ev: 0.19, confidence: "Medium", rationale: "35% top-5 vs. 28% fair — a +7pt edge; intermediate-oval speed and clean-air rating." }),
  S({ id: "s1", sport_id: "soccer", event_name: "Man City vs Arsenal", market: "moneyline", selection: "Draw", book: "pinnacle", price: 260, model_prob: 0.31, novig_prob: 0.263, ev: 0.116, confidence: "Low", rationale: "31% draw vs. 26% fair — a +4.7pt edge; matched xG and low-variance styles." }),
  S({ id: "f1", sport_id: "nfl", event_name: "Preseason: KC vs DET", market: "spread", selection: "Lions +3.5", book: "fanduel", price: -105, model_prob: 0.56, novig_prob: 0.512, ev: 0.092, confidence: "Low", rationale: "56% to cover vs. 51% fair — a +4.8pt edge; starters' snap projection favors Detroit early." }),
];

function sampleFor(filters: Filters): EvBet[] {
  return SAMPLE.filter(
    (b) =>
      b.ev >= filters.minEv &&
      (!filters.sport || b.sport_id === filters.sport) &&
      (!filters.market || b.market === filters.market)
  ).sort((a, b) => b.ev - a.ev);
}

export function useEvBets(filters: Filters) {
  return useQuery({
    queryKey: ["ev_bets", filters],
    queryFn: async (): Promise<EvBet[]> => {
      if (!supabaseConfigured || !supabase) return sampleFor(filters);
      try {
        // Embed the related event's name via the ev_bets.event_id FK, so the
        // board can show "The Open Championship" without a separate query.
        let q = supabase
          .from("ev_bets")
          .select("*, event:events(name)")
          .eq("status", "open")
          .gte("ev", filters.minEv)
          .order("ev", { ascending: false })
          .limit(200);
        if (filters.sport) q = q.eq("sport_id", filters.sport);
        if (filters.market) q = q.eq("market", filters.market);
        const { data, error } = await q;
        if (error) throw error;
        return ((data ?? []) as Array<EvBet & { event?: { name?: string } }>).map(
          ({ event, ...b }) => ({ ...b, event_name: b.event_name ?? event?.name })
        );
      } catch (e) {
        // DB unreachable / schema not created yet: show sample so the board is
        // never a broken error page. Seed the DB (supabase/seed.sql) for live rows.
        console.warn("[EDGE] Supabase fetch failed; showing sample data.", e);
        return sampleFor(filters);
      }
    },
    refetchInterval: 60_000, // +EV lines move; refresh each minute
  });
}

// Exposed so filter dropdowns can populate even before data loads.
export const ALL_SAMPLE = SAMPLE;
