# web

Next.js (App Router) + TypeScript dashboard. Reads `ev_bets` from Supabase (RLS +
anon key), ranks by EV, filters by sport / market / min-EV. TanStack Query + Table.

## Run
```bash
npm install          # (or pnpm install)
npm run dev          # http://localhost:3000
npm run build        # production build + typecheck (verified green)
```

Without `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` set, the page
renders **sample data** so you can explore the UI immediately (see `lib/useEvBets.ts`).

## Files
- `app/page.tsx` — the dashboard (sortable/filterable table + per-bet rationale).
- `lib/useEvBets.ts` — TanStack Query hook; Supabase query + sample fallback.
- `lib/supabase.ts` — browser client (anon key only; never the service role key).
- `lib/types.ts` — `EvBet` type. Replace with `supabase gen types typescript`.

## Notes
- Styling is Tailwind v4 (`@import "tailwindcss"` + `@tailwindcss/postcss`).
- Filter state is local `useState`; lift to Zustand if it grows (tech-stack §1).
