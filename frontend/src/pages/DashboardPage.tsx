import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowUpRight,
  Boxes,
  Calendar,
  Layers,
  Ruler,
  ShieldAlert,
  TrendingUp,
} from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getDashboardSummary } from "@/api/dashboard";
import { cn } from "@/lib/utils";
import type {
  DashboardProjectSummary,
  ProjectPhase,
  ProjectPriorite,
} from "@/types";

/**
 * Tableau de bord multi-projets (US-RA-01).
 *
 * Hierarchie visuelle :
 * 1. Bandeau compact en haut = totaux globaux (lecture rapide, filtres-raccourcis cliquables).
 * 2. Cartes projet en grand = un mini-dashboard par projet, KPI cliquables qui
 *    naviguent directement vers l'onglet concerne du projet (?tab=<id>).
 */
export default function DashboardPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: getDashboardSummary,
    staleTime: 30_000,
  });

  const [filter, setFilter] = useState<
    "tous" | "alertes" | "ecarts" | "en_cours" | "critique"
  >("tous");
  const [sortBy, setSortBy] = useState<
    | "alertes"
    | "avancement_asc"
    | "avancement_desc"
    | "ecarts"
    | "activite"
    | "priorite"
    | "deadline"
  >("alertes");

  const projets = useMemo(() => {
    if (!data) return [];
    let list = [...data.projets];
    if (filter === "alertes")
      list = list.filter(
        (p) => p.nb_alertes_stock > 0 || p.nb_ecarts_bloquants > 0
      );
    if (filter === "ecarts") list = list.filter((p) => p.nb_ecarts_ouverts > 0);
    if (filter === "en_cours")
      list = list.filter((p) => p.avancement_pct > 0 && p.avancement_pct < 100);
    if (filter === "critique")
      list = list.filter((p) => p.priorite === "critique");

    const score = (p: DashboardProjectSummary) =>
      p.nb_ecarts_bloquants * 100 + p.nb_alertes_stock * 10 + p.nb_ecarts_ouverts;
    const priWeight: Record<ProjectPriorite, number> = {
      critique: 3,
      standard: 2,
      faible: 1,
    };

    switch (sortBy) {
      case "alertes":
        list.sort((a, b) => score(b) - score(a));
        break;
      case "avancement_asc":
        list.sort((a, b) => a.avancement_pct - b.avancement_pct);
        break;
      case "avancement_desc":
        list.sort((a, b) => b.avancement_pct - a.avancement_pct);
        break;
      case "ecarts":
        list.sort((a, b) => b.nb_ecarts_ouverts - a.nb_ecarts_ouverts);
        break;
      case "activite":
        list.sort((a, b) => {
          const da = a.derniere_activite ? Date.parse(a.derniere_activite) : 0;
          const db = b.derniere_activite ? Date.parse(b.derniere_activite) : 0;
          return db - da;
        });
        break;
      case "priorite":
        list.sort((a, b) => priWeight[b.priorite] - priWeight[a.priorite]);
        break;
      case "deadline":
        list.sort((a, b) => {
          const da = a.date_fin_prevue ? Date.parse(a.date_fin_prevue) : Infinity;
          const db = b.date_fin_prevue ? Date.parse(b.date_fin_prevue) : Infinity;
          return da - db;
        });
        break;
    }
    return list;
  }, [data, filter, sortBy]);

  if (isLoading) {
    return (
      <div className="flex-1 min-h-0 overflow-auto p-6">
        <p className="text-sm text-text-tertiary">
          Chargement du tableau de bord...
        </p>
      </div>
    );
  }
  if (isError || !data) {
    return (
      <div className="flex-1 min-h-0 overflow-auto p-6">
        <p className="text-sm text-status-warn">
          Impossible de charger le tableau de bord.
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 min-h-0 overflow-auto p-4 sm:p-6 space-y-4">
      <div>
        <h1 className="text-lg sm:text-xl font-semibold text-text-primary">
          Tableau de bord
        </h1>
        <p className="text-xs text-text-tertiary mt-0.5">
          Vue d'ensemble du portefeuille de projets. Chaque carte ci-dessous
          est cliquable : ouvre la zone concernee du projet.
        </p>
      </div>

      {/* Bandeau compact totaux globaux ----------------------------------- */}
      <div className="bg-white border border-border-std rounded-lg">
        <div className="px-3 sm:px-4 py-2.5 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 sm:gap-3 text-xs">
          <TotalChip
            icon={<Layers size={13} />}
            label="Projets"
            value={`${data.nb_projets_actifs} / ${data.nb_projets}`}
            sub="actifs"
            active={filter === "tous"}
            onClick={() => setFilter("tous")}
          />
          <TotalChip
            icon={<TrendingUp size={13} />}
            label="Avancement moyen"
            value={`${data.avancement_moyen_pct.toFixed(0)} %`}
            active={filter === "en_cours"}
            onClick={() =>
              setFilter(filter === "en_cours" ? "tous" : "en_cours")
            }
          />
          <TotalChip
            icon={<ShieldAlert size={13} />}
            label="Ecarts ouverts"
            value={data.nb_ecarts_ouverts_total}
            sub={
              data.nb_ecarts_bloquants_total > 0
                ? `${data.nb_ecarts_bloquants_total} bloquants`
                : undefined
            }
            tone={data.nb_ecarts_bloquants_total > 0 ? "red" : "neutral"}
            active={filter === "ecarts"}
            onClick={() => setFilter(filter === "ecarts" ? "tous" : "ecarts")}
          />
          <TotalChip
            icon={<Boxes size={13} />}
            label="Alertes stock"
            value={data.nb_alertes_stock_total}
            tone={data.nb_alertes_stock_total > 0 ? "red" : "neutral"}
            active={filter === "alertes"}
            onClick={() => setFilter(filter === "alertes" ? "tous" : "alertes")}
          />
          <TotalChip
            icon={<Ruler size={13} />}
            label="Cable tire / prevu"
            value={`${formatMeters(data.longueur_realisee_totale_m)} m`}
            sub={`sur ${formatMeters(data.longueur_prevue_totale_m)} m`}
          />
          <TotalChip
            icon={<AlertTriangle size={13} />}
            label="Critiques"
            value={data.projets.filter((p) => p.priorite === "critique").length}
            tone="red"
            active={filter === "critique"}
            onClick={() =>
              setFilter(filter === "critique" ? "tous" : "critique")
            }
          />
        </div>
      </div>

      {/* Filtres complets + tri ------------------------------------------- */}
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex-1 min-w-[150px]">
          <label className="block text-[11px] text-text-tertiary mb-1">
            Filtrer
          </label>
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as typeof filter)}
            className="w-full text-xs border border-border-std rounded px-2 py-1.5 bg-white"
          >
            <option value="tous">Tous les projets</option>
            <option value="alertes">Avec alertes (bloquants / stock)</option>
            <option value="ecarts">Avec ecarts ouverts</option>
            <option value="en_cours">Chantier en cours</option>
            <option value="critique">Priorite critique</option>
          </select>
        </div>
        <div className="flex-1 min-w-[170px]">
          <label className="block text-[11px] text-text-tertiary mb-1">
            Trier par
          </label>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
            className="w-full text-xs border border-border-std rounded px-2 py-1.5 bg-white"
          >
            <option value="alertes">Criticite (bloquants d'abord)</option>
            <option value="priorite">Priorite RA</option>
            <option value="deadline">Echeance la plus proche</option>
            <option value="avancement_asc">Avancement croissant</option>
            <option value="avancement_desc">Avancement decroissant</option>
            <option value="ecarts">Ecarts ouverts</option>
            <option value="activite">Activite recente</option>
          </select>
        </div>
        {(filter !== "tous" || sortBy !== "alertes") && (
          <button
            type="button"
            onClick={() => {
              setFilter("tous");
              setSortBy("alertes");
            }}
            className="text-xs px-2 py-1.5 text-vinci-red hover:underline self-end"
          >
            Reinitialiser
          </button>
        )}
      </div>

      {/* Grille cartes projet --------------------------------------------- */}
      {projets.length === 0 ? (
        <div className="border border-dashed border-border-std rounded p-8 text-center">
          <p className="text-sm text-text-secondary">
            Aucun projet ne correspond aux filtres.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {projets.map((p) => (
            <ProjectCard key={p.id} project={p} />
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Bandeau totaux : composant chip compact, cliquable pour filtrer
// ---------------------------------------------------------------------------

function TotalChip({
  icon,
  label,
  value,
  sub,
  tone = "neutral",
  active,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  sub?: string;
  tone?: "neutral" | "red";
  active?: boolean;
  onClick?: () => void;
}) {
  const toneText =
    tone === "red" ? "text-vinci-red" : "text-text-primary";
  const interactive = !!onClick;
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!interactive}
      aria-pressed={active}
      className={cn(
        "flex items-center gap-2 text-left rounded px-2 py-1.5 transition-colors",
        interactive
          ? "hover:bg-vinci-blue/5 cursor-pointer"
          : "cursor-default",
        active && "bg-vinci-blue/10 ring-1 ring-vinci-blue/30"
      )}
    >
      <span
        className={cn(
          "shrink-0 inline-flex items-center justify-center w-6 h-6 rounded",
          tone === "red"
            ? "bg-vinci-red/10 text-vinci-red"
            : "bg-vinci-blue/10 text-vinci-blue"
        )}
      >
        {icon}
      </span>
      <div className="min-w-0">
        <div className={cn("font-semibold text-sm tabular-nums", toneText)}>
          {value}
        </div>
        <div className="text-[10px] text-text-tertiary leading-tight">
          {label}
          {sub && <span className="block">{sub}</span>}
        </div>
      </div>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Carte projet avec mini-dashboard interne
// ---------------------------------------------------------------------------

const PHASE_LABELS: Record<ProjectPhase, string> = {
  etudes: "Etudes",
  approvisionnement: "Appro",
  pose: "Pose",
  mise_en_service: "MES",
  reception: "Reception",
};

const PHASE_BG: Record<ProjectPhase, string> = {
  etudes: "bg-blue-100 text-blue-800",
  approvisionnement: "bg-yellow-100 text-yellow-800",
  pose: "bg-vinci-blue/10 text-vinci-blue",
  mise_en_service: "bg-purple-100 text-purple-800",
  reception: "bg-green-100 text-green-800",
};

const PRIORITE_BG: Record<ProjectPriorite, string> = {
  critique: "bg-vinci-red text-white",
  standard: "bg-bg-cell text-text-secondary",
  faible: "bg-bg-cell text-text-tertiary",
};

function ProjectCard({ project }: { project: DashboardProjectSummary }) {
  const navigate = useNavigate();
  const hasBlockers =
    project.nb_ecarts_bloquants > 0 || project.nb_alertes_stock > 0;
  const isCritique = project.priorite === "critique";

  const goTab = (tab: string) => navigate(`/projects/${project.id}?tab=${tab}`);

  const deadlineInfo = project.date_fin_prevue
    ? describeDeadline(project.date_fin_prevue)
    : null;

  return (
    <div
      className={cn(
        "bg-white border rounded-lg overflow-hidden transition-shadow hover:shadow-md",
        isCritique
          ? "border-vinci-red/50"
          : hasBlockers
          ? "border-vinci-red/30"
          : "border-border-std"
      )}
    >
      {/* Header cliquable -> page projet */}
      <button
        type="button"
        onClick={() => navigate(`/projects/${project.id}`)}
        className="w-full text-left px-4 py-3 border-b border-border-std hover:bg-vinci-blue/5 transition-colors"
      >
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[10px] uppercase tracking-wide text-text-tertiary">
                {project.code}
              </span>
              <span
                className={cn(
                  "text-[10px] px-1.5 py-0.5 rounded uppercase tracking-wide",
                  project.status === "actif"
                    ? "bg-green-100 text-green-800"
                    : "bg-bg-cell text-text-tertiary"
                )}
              >
                {project.status}
              </span>
              <span
                className={cn(
                  "text-[10px] px-1.5 py-0.5 rounded font-medium",
                  PHASE_BG[project.phase]
                )}
              >
                {PHASE_LABELS[project.phase]}
              </span>
              <span
                className={cn(
                  "text-[10px] px-1.5 py-0.5 rounded font-medium",
                  PRIORITE_BG[project.priorite]
                )}
              >
                {project.priorite}
              </span>
              {project.indice_caneco && (
                <span className="text-[10px] text-text-tertiary">
                  Indice {project.indice_caneco}
                </span>
              )}
            </div>
            <h3 className="text-base font-semibold text-vinci-blue truncate mt-1">
              {project.name}
            </h3>
            <p className="text-xs text-text-tertiary truncate">
              {project.client ?? "—"}
              {project.agency ? ` · ${project.agency}` : ""}
            </p>
          </div>
          <ArrowUpRight size={18} className="text-text-tertiary shrink-0 mt-1" />
        </div>
      </button>

      {/* Avancement compose ------------------------------------------------ */}
      <button
        type="button"
        onClick={() => goTab("saisie-chantier")}
        title="Ouvrir la saisie chantier"
        className="w-full text-left px-4 py-3 border-b border-border-std hover:bg-vinci-blue/5 transition-colors"
      >
        <div className="flex items-center justify-between text-[11px] text-text-tertiary mb-1.5">
          <span>
            Avancement projet — tirets {project.pct_tirets.toFixed(0)} %
            {" · "}
            validation {project.validation_pct.toFixed(0)} %
          </span>
          <span className="font-semibold text-text-primary text-sm">
            {project.avancement_pct.toFixed(0)} %
          </span>
        </div>
        <div className="h-2.5 bg-bg-cell rounded overflow-hidden">
          <div
            className={cn(
              "h-full transition-all",
              project.avancement_pct >= 80
                ? "bg-green-500"
                : project.avancement_pct >= 30
                ? "bg-vinci-blue"
                : "bg-vinci-red/70"
            )}
            style={{ width: `${Math.min(100, project.avancement_pct)}%` }}
          />
        </div>
        <div className="text-[10px] text-text-tertiary mt-1.5">
          {project.nb_circuits_saisis} / {project.nb_circuits} circuits saisis{" "}
          · {formatMeters(project.longueur_realisee_m)} m tires sur{" "}
          {formatMeters(project.longueur_prevue_m)} m
        </div>
      </button>

      {/* Grille KPI cliquables --------------------------------------------- */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-border-std">
        <MiniKpi
          icon={<ShieldAlert size={13} />}
          label="Ecarts"
          value={project.nb_ecarts_ouverts}
          critical={project.nb_ecarts_bloquants > 0}
          hint={
            project.nb_ecarts_bloquants > 0
              ? `${project.nb_ecarts_bloquants} bloquants`
              : "Verifications"
          }
          onClick={() => goTab("verifications")}
        />
        <MiniKpi
          icon={<Boxes size={13} />}
          label="Alertes stock"
          value={project.nb_alertes_stock}
          critical={project.nb_alertes_stock > 0}
          hint="Stock cables"
          onClick={() => goTab("stock-cables")}
        />
        <MiniKpi
          icon={<Layers size={13} />}
          label="Tableaux"
          value={project.nb_tableaux}
          hint="Voir les tableaux"
          onClick={() => goTab("tableaux")}
        />
        <MiniKpi
          icon={<Ruler size={13} />}
          label="Carnet"
          value={`${formatMeters(project.longueur_prevue_m)} m`}
          hint="Carnet cables"
          onClick={() => goTab("cable-book")}
          small
        />
      </div>

      {/* Footer : deadline + activite ------------------------------------- */}
      <div className="px-4 py-2 flex items-center justify-between text-[11px] text-text-tertiary bg-bg-cell/40">
        {deadlineInfo ? (
          <span
            className={cn(
              "flex items-center gap-1",
              deadlineInfo.tone === "red" && "text-vinci-red font-medium",
              deadlineInfo.tone === "amber" && "text-yellow-700"
            )}
          >
            <Calendar size={11} />
            {deadlineInfo.label}
          </span>
        ) : (
          <span className="flex items-center gap-1 opacity-60">
            <Calendar size={11} />
            Aucune deadline
          </span>
        )}
        {project.derniere_activite ? (
          <span>Activite : {formatRelative(project.derniere_activite)}</span>
        ) : (
          <span className="opacity-60">Pas d'activite</span>
        )}
      </div>
    </div>
  );
}

function MiniKpi({
  icon,
  label,
  value,
  critical,
  hint,
  onClick,
  small,
}: {
  icon: React.ReactNode;
  label: string;
  value: number | string;
  critical?: boolean;
  hint?: string;
  onClick?: () => void;
  small?: boolean;
}) {
  const hasValue = typeof value === "number" ? value > 0 : true;
  return (
    <button
      type="button"
      onClick={onClick}
      title={hint}
      className={cn(
        "bg-white p-2.5 text-left transition-colors group",
        onClick ? "hover:bg-vinci-blue/5 cursor-pointer" : "cursor-default"
      )}
    >
      <div
        className={cn(
          "flex items-center gap-1 text-[10px] uppercase tracking-wide",
          critical && hasValue
            ? "text-vinci-red"
            : hasValue
            ? "text-vinci-blue"
            : "text-text-tertiary"
        )}
      >
        {icon}
        <span>{label}</span>
        {critical && hasValue && (
          <AlertTriangle size={10} className="ml-auto" />
        )}
      </div>
      <div
        className={cn(
          "font-bold mt-0.5 tabular-nums",
          small ? "text-sm" : "text-lg",
          critical && hasValue
            ? "text-vinci-red"
            : "text-text-primary"
        )}
      >
        {value}
      </div>
      {hint && (
        <div className="text-[10px] text-text-tertiary mt-0.5 truncate flex items-center gap-0.5 group-hover:text-vinci-blue transition-colors">
          {hint}
          <ArrowUpRight size={10} className="opacity-60" />
        </div>
      )}
    </button>
  );
}

function formatMeters(m: number): string {
  return new Intl.NumberFormat("fr-FR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(m);
}

function formatRelative(iso: string): string {
  const d = new Date(iso);
  const diff = Date.now() - d.getTime();
  const sec = Math.round(diff / 1000);
  if (sec < 60) return "a l'instant";
  if (sec < 3600) return `il y a ${Math.round(sec / 60)} min`;
  if (sec < 86400) return `il y a ${Math.round(sec / 3600)} h`;
  return d.toLocaleDateString("fr-FR");
}

function describeDeadline(
  iso: string
): { label: string; tone: "neutral" | "amber" | "red" } {
  const d = new Date(iso);
  const days = Math.round((d.getTime() - Date.now()) / 86400_000);
  const fmt = d.toLocaleDateString("fr-FR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
  if (days < 0)
    return { label: `Echeance depassee : ${fmt}`, tone: "red" };
  if (days <= 14) return { label: `Fin dans ${days} j (${fmt})`, tone: "amber" };
  return { label: `Fin prevue : ${fmt}`, tone: "neutral" };
}

