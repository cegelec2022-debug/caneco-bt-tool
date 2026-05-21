import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowUpRight,
  Boxes,
  CheckCircle2,
  ShieldAlert,
  TrendingUp,
} from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getDashboardSummary } from "@/api/dashboard";
import { cn } from "@/lib/utils";
import type { DashboardProjectSummary } from "@/types";

/**
 * Tableau de bord multi-projets (US-RA-01).
 * Le RA voit en un coup d'oeil les projets actifs, l'avancement chantier,
 * les ecarts ouverts, les alertes stock, et peut drill-down vers chaque projet.
 */
export default function DashboardPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: getDashboardSummary,
    staleTime: 30_000,
  });

  const [filter, setFilter] = useState<
    "tous" | "alertes" | "ecarts" | "en_cours"
  >("tous");
  const [sortBy, setSortBy] = useState<
    "alertes" | "avancement_asc" | "avancement_desc" | "ecarts" | "activite"
  >("alertes");

  const projets = useMemo(() => {
    if (!data) return [];
    let list = [...data.projets];
    if (filter === "alertes")
      list = list.filter((p) => p.nb_alertes_stock > 0 || p.nb_ecarts_bloquants > 0);
    if (filter === "ecarts") list = list.filter((p) => p.nb_ecarts_ouverts > 0);
    if (filter === "en_cours")
      list = list.filter((p) => p.avancement_pct > 0 && p.avancement_pct < 100);

    const score = (p: DashboardProjectSummary) =>
      p.nb_ecarts_bloquants * 100 + p.nb_alertes_stock * 10 + p.nb_ecarts_ouverts;

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
    }
    return list;
  }, [data, filter, sortBy]);

  if (isLoading) {
    return (
      <div className="flex-1 min-h-0 overflow-auto p-6">
        <p className="text-sm text-text-tertiary">Chargement du tableau de bord...</p>
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
    <div className="flex-1 min-h-0 overflow-auto p-4 sm:p-6 space-y-5">
      <div>
        <h1 className="text-lg sm:text-xl font-semibold text-text-primary">
          Tableau de bord
        </h1>
        <p className="text-xs text-text-tertiary mt-0.5">
          {data.nb_projets_actifs} projet{data.nb_projets_actifs > 1 ? "s" : ""}{" "}
          actif{data.nb_projets_actifs > 1 ? "s" : ""} ·{" "}
          {data.nb_projets} au total
        </p>
      </div>

      {/* KPI globaux — cliquables, chacun applique un filtre rapide */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <KpiBlock
          icon={<TrendingUp size={16} />}
          label="Avancement moyen"
          value={`${data.avancement_moyen_pct.toFixed(0)}%`}
          tone="blue"
          active={filter === "en_cours"}
          onClick={() =>
            setFilter(filter === "en_cours" ? "tous" : "en_cours")
          }
          actionHint="Voir les chantiers en cours"
        />
        <KpiBlock
          icon={<ShieldAlert size={16} />}
          label="Ecarts ouverts"
          sub={
            data.nb_ecarts_bloquants_total > 0
              ? `${data.nb_ecarts_bloquants_total} bloquant${
                  data.nb_ecarts_bloquants_total > 1 ? "s" : ""
                }`
              : undefined
          }
          value={data.nb_ecarts_ouverts_total}
          tone={data.nb_ecarts_bloquants_total > 0 ? "red" : "neutral"}
          active={filter === "ecarts"}
          onClick={() => setFilter(filter === "ecarts" ? "tous" : "ecarts")}
          actionHint="Filtrer les projets avec ecarts"
        />
        <KpiBlock
          icon={<Boxes size={16} />}
          label="Alertes stock"
          value={data.nb_alertes_stock_total}
          tone={data.nb_alertes_stock_total > 0 ? "red" : "neutral"}
          active={filter === "alertes"}
          onClick={() =>
            setFilter(filter === "alertes" ? "tous" : "alertes")
          }
          actionHint="Filtrer les projets avec alertes critiques"
        />
        <KpiBlock
          icon={<CheckCircle2 size={16} />}
          label="Cable tire / prevu"
          value={`${formatMeters(data.longueur_realisee_totale_m)} m`}
          sub={`sur ${formatMeters(data.longueur_prevue_totale_m)} m`}
          tone="neutral"
          active={sortBy === "avancement_desc"}
          onClick={() =>
            setSortBy(
              sortBy === "avancement_desc" ? "alertes" : "avancement_desc"
            )
          }
          actionHint="Trier par avancement decroissant"
        />
      </div>

      {/* Filtres et tri */}
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex-1 min-w-[140px]">
          <label className="block text-[11px] text-text-tertiary mb-1">Filtrer</label>
          <select
            value={filter}
            onChange={(e) =>
              setFilter(e.target.value as typeof filter)
            }
            className="w-full text-xs border border-border-std rounded px-2 py-1.5 bg-white"
          >
            <option value="tous">Tous les projets</option>
            <option value="alertes">Avec alertes (bloquants / stock)</option>
            <option value="ecarts">Avec ecarts ouverts</option>
            <option value="en_cours">Chantier en cours</option>
          </select>
        </div>
        <div className="flex-1 min-w-[160px]">
          <label className="block text-[11px] text-text-tertiary mb-1">Trier par</label>
          <select
            value={sortBy}
            onChange={(e) =>
              setSortBy(e.target.value as typeof sortBy)
            }
            className="w-full text-xs border border-border-std rounded px-2 py-1.5 bg-white"
          >
            <option value="alertes">Criticite (bloquants d'abord)</option>
            <option value="avancement_asc">Avancement croissant</option>
            <option value="avancement_desc">Avancement decroissant</option>
            <option value="ecarts">Ecarts ouverts</option>
            <option value="activite">Activite recente</option>
          </select>
        </div>
      </div>

      {/* Grille des projets */}
      {projets.length === 0 ? (
        <div className="border border-dashed border-border-std rounded p-8 text-center">
          <p className="text-sm text-text-secondary">
            Aucun projet ne correspond aux filtres.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {projets.map((p) => (
            <ProjectCard key={p.id} project={p} />
          ))}
        </div>
      )}
    </div>
  );
}

function KpiBlock({
  icon,
  label,
  value,
  sub,
  tone,
  active,
  onClick,
  actionHint,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  sub?: string;
  tone: "blue" | "red" | "neutral";
  active?: boolean;
  onClick?: () => void;
  actionHint?: string;
}) {
  const toneClass =
    tone === "blue"
      ? "bg-vinci-blue/5 border-vinci-blue/20 text-vinci-blue"
      : tone === "red"
      ? "bg-vinci-red/5 border-vinci-red/30 text-vinci-red"
      : "bg-bg-cell border-border-std text-text-primary";
  const interactive = !!onClick;
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!interactive}
      aria-pressed={active}
      title={actionHint}
      className={cn(
        "border rounded p-3 text-left transition-all",
        toneClass,
        interactive &&
          "cursor-pointer hover:shadow-sm hover:-translate-y-0.5 active:translate-y-0",
        active && "ring-2 ring-vinci-blue/30",
        !interactive && "cursor-default"
      )}
    >
      <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wide opacity-80">
        {icon}
        {label}
      </div>
      <div className="text-xl sm:text-2xl font-bold mt-1">{value}</div>
      {sub && <div className="text-[11px] opacity-70 mt-0.5">{sub}</div>}
    </button>
  );
}

function ProjectCard({ project }: { project: DashboardProjectSummary }) {
  const navigate = useNavigate();
  const hasBlockers =
    project.nb_ecarts_bloquants > 0 || project.nb_alertes_stock > 0;

  return (
    <button
      type="button"
      onClick={() => navigate(`/projects/${project.id}`)}
      className={cn(
        "text-left bg-white border rounded-lg p-4 transition-all hover:shadow-md",
        hasBlockers
          ? "border-vinci-red/40 hover:border-vinci-red"
          : "border-border-std hover:border-vinci-blue/40"
      )}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
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
            {project.indice_caneco && (
              <span className="text-[10px] text-text-tertiary">
                Indice {project.indice_caneco}
              </span>
            )}
          </div>
          <h3 className="text-sm font-semibold text-vinci-blue truncate mt-0.5">
            {project.name}
          </h3>
          <p className="text-xs text-text-tertiary truncate">
            {project.client ?? "—"}
            {project.agency ? ` · ${project.agency}` : ""}
          </p>
        </div>
        <ArrowUpRight size={16} className="text-text-tertiary shrink-0" />
      </div>

      {/* Avancement chantier */}
      <div className="mt-3">
        <div className="flex items-center justify-between text-[11px] text-text-tertiary mb-1">
          <span>
            Avancement chantier ({project.nb_circuits_saisis} /{" "}
            {project.nb_circuits} circuits)
          </span>
          <span className="font-semibold text-text-primary">
            {project.avancement_pct.toFixed(0)}%
          </span>
        </div>
        <div className="h-2 bg-bg-cell rounded overflow-hidden">
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
        <div className="text-[10px] text-text-tertiary mt-1">
          {formatMeters(project.longueur_realisee_m)} m tires /{" "}
          {formatMeters(project.longueur_prevue_m)} m prevus
        </div>
      </div>

      {/* Indicateurs critiques */}
      <div className="flex flex-wrap gap-2 mt-3">
        <PillStat
          icon={<ShieldAlert size={11} />}
          label="Ecarts"
          value={project.nb_ecarts_ouverts}
          critical={project.nb_ecarts_bloquants > 0}
          criticalSuffix={
            project.nb_ecarts_bloquants > 0
              ? `${project.nb_ecarts_bloquants} bloquant${
                  project.nb_ecarts_bloquants > 1 ? "s" : ""
                }`
              : undefined
          }
        />
        <PillStat
          icon={<Boxes size={11} />}
          label="Alertes stock"
          value={project.nb_alertes_stock}
          critical={project.nb_alertes_stock > 0}
        />
        <PillStat
          icon={<TrendingUp size={11} />}
          label="Tableaux"
          value={project.nb_tableaux}
        />
      </div>

      {project.derniere_activite && (
        <p className="text-[10px] text-text-tertiary mt-3">
          Activite : {formatRelative(project.derniere_activite)}
        </p>
      )}
    </button>
  );
}

function PillStat({
  icon,
  label,
  value,
  critical,
  criticalSuffix,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  critical?: boolean;
  criticalSuffix?: string;
}) {
  const hasValue = value > 0;
  return (
    <div
      className={cn(
        "inline-flex items-center gap-1.5 text-[11px] px-2 py-0.5 rounded border",
        critical && hasValue
          ? "bg-vinci-red/10 border-vinci-red/40 text-vinci-red"
          : hasValue
          ? "bg-vinci-blue/5 border-vinci-blue/20 text-vinci-blue"
          : "bg-bg-cell border-border-std text-text-tertiary"
      )}
      title={criticalSuffix}
    >
      {icon}
      <span className="font-medium">{value}</span>
      <span className="opacity-80">{label}</span>
      {criticalSuffix && <AlertTriangle size={10} className="ml-0.5" />}
    </div>
  );
}

function formatMeters(m: number): string {
  return new Intl.NumberFormat("fr-FR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 1,
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
