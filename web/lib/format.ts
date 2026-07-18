// Shared formatting for odds / probabilities / EV. American odds are integers.

export const fmtOdds = (p: number) => (p > 0 ? `+${p}` : `${p}`);

export const fmtPct = (x: number | null | undefined, d = 1) =>
  x == null ? "—" : `${(x * 100).toFixed(d)}%`;

export const fmtEv = (x: number) => `${x >= 0 ? "+" : ""}${(x * 100).toFixed(1)}%`;

export const fmtKelly = (x: number | null | undefined) =>
  x == null ? "—" : `${(x * 100).toFixed(2)}%`;

export function decimalFromAmerican(price: number): number {
  return price > 0 ? price / 100 + 1 : 100 / -price + 1;
}

// Potential profit for 1 unit staked at American odds.
export function profitPerUnit(price: number): number {
  return decimalFromAmerican(price) - 1;
}

export const SPORT_META: Record<string, { label: string; icon: string }> = {
  golf: { label: "Golf", icon: "⛳" },
  nfl: { label: "NFL", icon: "🏈" },
  ncaab: { label: "NCAA Basketball", icon: "🏀" },
  ncaaf: { label: "NCAA Football", icon: "🏈" },
  soccer: { label: "Soccer", icon: "⚽" },
  nascar: { label: "NASCAR", icon: "🏁" },
};

export const MARKET_LABEL: Record<string, string> = {
  make_cut: "Make Cut",
  top_5: "Top 5",
  top_10: "Top 10",
  top_20: "Top 20",
  moneyline: "Moneyline",
  spread: "Spread",
  outright: "Outright",
};

export const sportMeta = (id: string) =>
  SPORT_META[id] ?? { label: id, icon: "•" };
export const marketLabel = (id: string) => MARKET_LABEL[id] ?? id;
