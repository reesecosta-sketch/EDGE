// Mirrors the ev_bets row the worker writes (see supabase/migrations/0001_init.sql),
// plus optional UI-only fields the prototype renders when present.
// TODO: replace with generated types: `supabase gen types typescript`.
export type EvBet = {
  id: string;
  sport_id: string;
  event_id: string;
  market: string;
  selection: string;
  book: string;
  price: number; // American odds
  model_prob: number; // 0..1
  novig_prob: number | null;
  ev: number; // fraction, e.g. 0.043
  kelly_frac: number | null;
  rationale: string | null;
  flagged_at: string;
  status: string;
  // optional UI extras (present in sample / future event joins)
  event_name?: string;
  confidence?: "High" | "Medium" | "Low";
  trust_tier?: "experimental" | "trusted";
};
