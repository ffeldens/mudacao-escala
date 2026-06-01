/**
 * Helpers de autenticação reutilizáveis em Server Components.
 *
 * - getCurrentUser(): retorna o user logado ou null
 * - requireUser(): retorna o user logado ou redireciona pra /login
 * - getUserProfile(): retorna o profile completo (com plan_tier etc)
 */

import { redirect } from "next/navigation";
import { createSupabaseServerClient } from "./server";

export interface UserProfile {
  id: string;
  email: string;
  nome: string | null;
  empresa: string | null;
  whatsapp: string | null;
  plan_tier: "free" | "starter" | "pro" | "enterprise";
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
  subscription_status:
    | "trialing"
    | "active"
    | "past_due"
    | "canceled"
    | null;
  trial_end_at: string | null;
  subscription_current_period_end: string | null;
  cancel_at_period_end: boolean;
  created_at: string;
  updated_at: string;
}

export async function getCurrentUser() {
  const supabase = createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  return user;
}

export async function requireUser() {
  const user = await getCurrentUser();
  if (!user) redirect("/login");
  return user;
}

export async function getUserProfile(): Promise<UserProfile | null> {
  const supabase = createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return null;

  const { data: profile, error } = await supabase
    .schema("freemium")
    .from("user_profiles")
    .select("*")
    .eq("id", user.id)
    .single();

  if (error) {
    // Profile não existe ainda? O trigger DB cria automaticamente, mas
    // edge case: race condition. Retornamos null e UI lida com isso.
    return null;
  }

  return profile as UserProfile;
}
