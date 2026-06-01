import Link from "next/link";
import { Crown, Sparkles, ArrowRight } from "lucide-react";
import type { UserProfile } from "@/lib/supabase/auth";
import { ManageSubscriptionButton } from "./ManageSubscriptionButton";

const PLAN_LABELS = {
  free: "Free",
  starter: "Starter",
  pro: "Pro",
  enterprise: "Enterprise",
} as const;

const PLAN_PRICES = {
  free: "Gratuito",
  starter: "R$ 99/mês",
  pro: "R$ 299/mês",
  enterprise: "Sob consulta",
} as const;

interface PlanCardProps {
  profile: UserProfile | null;
}

export function PlanCard({ profile }: PlanCardProps) {
  const tier = profile?.plan_tier ?? "free";
  const status = profile?.subscription_status;

  const isTrialing = status === "trialing";
  const isActive = status === "active";
  const isPastDue = status === "past_due";
  const isCanceled = status === "canceled";

  const trialEndsAt = profile?.trial_end_at
    ? new Date(profile.trial_end_at)
    : null;
  const periodEndsAt = profile?.subscription_current_period_end
    ? new Date(profile.subscription_current_period_end)
    : null;

  const accentBg =
    tier === "free"
      ? "bg-slate-50 border-slate-200"
      : "bg-gradient-to-br from-mudacao-900 to-mudacao-700 border-mudacao-700 text-white";

  const accentText = tier === "free" ? "text-mudacao-700" : "text-mudacao-100";
  const accentTitle = tier === "free" ? "text-mudacao-950" : "text-white";

  return (
    <section
      className={`rounded-2xl border-2 p-6 shadow-sm ${accentBg}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className={`text-xs font-bold uppercase tracking-widest ${accentText}`}>
            Seu plano
          </p>
          <h2 className={`mt-1 text-2xl font-bold ${accentTitle}`}>
            {PLAN_LABELS[tier]}
            <span className={`ml-2 text-sm font-normal ${accentText}`}>
              {PLAN_PRICES[tier]}
            </span>
          </h2>

          {isTrialing && trialEndsAt && (
            <p className={`mt-2 text-sm ${accentText}`}>
              ⏳ Trial gratuito até{" "}
              <strong>{trialEndsAt.toLocaleDateString("pt-BR")}</strong>
            </p>
          )}
          {isActive && periodEndsAt && (
            <p className={`mt-2 text-sm ${accentText}`}>
              ✓ Próxima cobrança em{" "}
              <strong>{periodEndsAt.toLocaleDateString("pt-BR")}</strong>
            </p>
          )}
          {isPastDue && (
            <p className="mt-2 rounded-lg bg-red-100 px-3 py-2 text-sm text-red-900">
              ⚠️ Pagamento pendente — atualize seu cartão pra não perder o
              acesso.
            </p>
          )}
          {isCanceled && (
            <p className={`mt-2 text-sm ${accentText}`}>
              Plano cancelado. Você ainda tem acesso até{" "}
              {periodEndsAt?.toLocaleDateString("pt-BR")}.
            </p>
          )}
        </div>

        {tier !== "free" && (
          <Crown className={`h-8 w-8 flex-shrink-0 ${accentText}`} />
        )}
      </div>

      {/* CTA: free vê "Assinar"; paid vê "Gerenciar" */}
      <div className="mt-6 flex flex-wrap gap-3">
        {tier === "free" ? (
          <Link
            href="/precos"
            className="inline-flex items-center gap-2 rounded-lg bg-mudacao-900 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-mudacao-700"
          >
            <Sparkles className="h-4 w-4" />
            Conhecer planos pagos
            <ArrowRight className="h-4 w-4" />
          </Link>
        ) : (
          <ManageSubscriptionButton />
        )}
      </div>
    </section>
  );
}
