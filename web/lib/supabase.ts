import { createClient, SupabaseClient } from "@supabase/supabase-js";

// Public Supabase config. The URL and the PUBLISHABLE key are safe to expose in
// the browser BY DESIGN — they ship in the client bundle, and Row-Level Security
// is the actual security layer. Committing them is fine.
// The secret / service-role key must NEVER appear here or anywhere in web/.
// Env vars (e.g. in Netlify) override these defaults for other environments.
const DEFAULT_URL = "https://ytswtgtojovuohmyoqfw.supabase.co";
const DEFAULT_PUBLISHABLE_KEY = "sb_publishable_ljXgiR7RYTYn9l-kXSVXKw_WF7Zu7oe";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL ?? DEFAULT_URL;
const publicKey =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ??
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ??
  DEFAULT_PUBLISHABLE_KEY;

export const supabaseConfigured = Boolean(url && publicKey);

export const supabase: SupabaseClient | null = supabaseConfigured
  ? createClient(url, publicKey)
  : null;
