import { createClient, SupabaseClient } from "@supabase/supabase-js";

// Browser-safe client: uses the PUBLIC key (anon / publishable) + RLS.
// NEVER the service-role or secret key. Accepts either the classic
// NEXT_PUBLIC_SUPABASE_ANON_KEY or Supabase's newer NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY.
const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const publicKey =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ??
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

export const supabaseConfigured = Boolean(url && publicKey);

export const supabase: SupabaseClient | null = supabaseConfigured
  ? createClient(url!, publicKey!)
  : null;
