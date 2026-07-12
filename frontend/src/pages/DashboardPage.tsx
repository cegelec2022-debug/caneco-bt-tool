import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowUpRight,
  Boxes,
  Calendar,
  ChevronRight,
  Layers,
  Ruler,
  ShieldAlert,
  TrendingUp,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getCableStock } from "@/api/cable_stock";
import { getDashboardSummary } from "@/api/dashboard";
import { listGaps, listVerificationRuns } from "@/api/verification";
import { cn } from "@/lib/utils";
import type {
  CableStockItemRow,
  DashboardProjectSummary,
  Gap,
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

  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(
    null
  );
  const [showStockAlerts, setShowStockAlerts] = useState(false);
  const [showBlockingGaps, setShowBlockingGaps] = useState(false);

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

  // Reset selection if filter/sort excludes the selected project, ou si le
  // projet n'existe plus dans la liste filtree.
  useEffect(() => {
    if (
      selectedProjectId &&
      !projets.some((p) => p.id === selectedProjectId)
    ) {
      setSelectedProjectId(null);
      setShowStockAlerts(false);
    }
  }, [projets, selectedProjectId]);

  // Fermer les popovers quand on change de projet selectionne.
  useEffect(() => {
    setShowStockAlerts(false);
    setShowBlockingGaps(false);
  }, [selectedProjectId]);

  const selectedProject = selectedProjectId
    ? projets.find((p) => p.id === selectedProjectId) ?? null
    : null;

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

      {/* Vue projets ------------------------------------------------------ */}
      {projets.length === 0 ? (
        <div className="border border-dashed border-border-std rounded p-8 text-center">
          <p className="text-sm text-text-secondary">
            Aucun projet ne correspond aux filtres.
          </p>
        </div>
      ) : selectedProject ? (
        <div className="space-y-3">
          <button
            type="button"
            onClick={() => setSelectedProjectId(null)}
            className="inline-flex items-center gap-1 text-xs text-vinci-blue hover:underline"
          >
            <ArrowLeft size={14} />
            Retour a la liste des projets
          </button>
          <ProjectCard
            project={selectedProject}
            onStockAlertClick={() => {
              setShowStockAlerts(true);
              setShowBlockingGaps(false);
            }}
            onBlockerClick={() => {
              setShowBlockingGaps(true);
              setShowStockAlerts(false);
            }}
          />
          {showBlockingGaps && (
            <BlockingGapsPanel
              projectId={selectedProject.id}
              projectCode={selectedProject.code}
              onClose={() => setShowBlockingGaps(false)}
            />
          )}
          {showStockAlerts && (
            <StockAlertsPanel
              projectId={selectedProject.id}
              projectCode={selectedProject.code}
              onClose={() => setShowStockAlerts(false)}
            />
          )}
        </div>
      ) : (
        <ProjectsListView projects={projets} onSelect={setSelectedProjectId} />
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

function ProjectCard({
  project,
  onStockAlertClick,
  onBlockerClick,
}: {
  project: DashboardProjectSummary;
  onStockAlertClick?: () => void;
  onBlockerClick?: () => void;
}) {
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
          value={project.nb_ecarts_bloquants}
          critical={project.nb_ecarts_bloquants > 0}
          hint={
            project.nb_ecarts_bloquants > 0
              ? `${project.nb_ecarts_bloquants} bloquant${
                  project.nb_ecarts_bloquants > 1 ? "s" : ""
                }${onBlockerClick ? " - Voir le resume" : ""}`
              : onBlockerClick
              ? "Aucun bloquant"
              : "Aucun bloquant"
          }
          onClick={
            onBlockerClick ? onBlockerClick : () => goTab("verifications")
          }
        />
        <MiniKpi
          icon={<Boxes size={13} />}
          label="Alertes stock"
          value={project.nb_alertes_stock}
          critical={project.nb_alertes_stock > 0}
          hint={
            onStockAlertClick ? "Voir le resume" : "Stock cables"
          }
          onClick={
            onStockAlertClick
              ? onStockAlertClick
              : () => goTab("stock-cables")
          }
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

// ---------------------------------------------------------------------------
// Vue liste : un projet par ligne, clic = ouvre la synthese du projet seul
// ---------------------------------------------------------------------------

function ProjectsListView({
  projects,
  onSelect,
}: {
  projects: DashboardProjectSummary[];
  onSelect: (id: string) => void;
}) {
  return (
    <div className="bg-white border border-border-std rounded-lg overflow-hidden">
      <div className="px-3 sm:px-4 py-2 border-b border-border-std bg-bg-cell/40">
        <p className="text-[11px] text-text-tertiary">
          Selectionnez un projet pour afficher sa synthese.
        </p>
      </div>
      <ul className="divide-y divide-border-std">
        {projects.map((p) => {
          const hasBlockers =
            p.nb_ecarts_bloquants > 0 || p.nb_alertes_stock > 0;
          const isCritique = p.priorite === "critique";
          return (
            <li key={p.id}>
              <button
                type="button"
                onClick={() => onSelect(p.id)}
                className={cn(
                  "w-full text-left px-3 sm:px-4 py-3 hover:bg-vinci-blue/5 transition-colors flex items-center gap-3",
                  isCritique && "bg-vinci-red/[0.03]"
                )}
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[10px] uppercase tracking-wide text-text-tertiary">
                      {p.code}
                    </span>
                    <span
                      className={cn(
                        "text-[10px] px-1.5 py-0.5 rounded uppercase tracking-wide",
                        p.status === "actif"
                          ? "bg-green-100 text-green-800"
                          : "bg-bg-cell text-text-tertiary"
                      )}
                    >
                      {p.status}
                    </span>
                    <span
                      className={cn(
                        "text-[10px] px-1.5 py-0.5 rounded font-medium",
                        PHASE_BG[p.phase]
                      )}
                    >
                      {PHASE_LABELS[p.phase]}
                    </span>
                    <span
                      className={cn(
                        "text-[10px] px-1.5 py-0.5 rounded font-medium",
                        PRIORITE_BG[p.priorite]
                      )}
                    >
                      {p.priorite}
                    </span>
                    {p.indice_caneco && (
                      <span className="text-[10px] text-text-tertiary">
                        Indice {p.indice_caneco}
                      </span>
                    )}
                  </div>
                  <div className="mt-1 flex items-baseline gap-2 flex-wrap">
                    <h3 className="text-sm sm:text-base font-semibold text-vinci-blue truncate">
                      {p.name}
                    </h3>
                    <span className="text-[11px] text-text-tertiary">
                      {p.client ?? "—"}
                      {p.agency ? ` · ${p.agency}` : ""}
                    </span>
                  </div>
                  <div className="mt-1 flex items-center gap-3 flex-wrap text-[11px] text-text-secondary">
                    <span>
                      Avancement{" "}
                      <span className="font-semibold text-text-primary">
                        {p.avancement_pct.toFixed(0)} %
                      </span>
                    </span>
                    <span
                      className={cn(
                        p.nb_ecarts_bloquants > 0 && "text-vinci-red font-medium"
                      )}
                    >
                      {p.nb_ecarts_ouverts} ecarts
                      {p.nb_ecarts_bloquants > 0
                        ? ` (${p.nb_ecarts_bloquants} bloquants)`
                        : ""}
                    </span>
                    <span
                      className={cn(
                        p.nb_alertes_stock > 0 && "text-vinci-red font-medium"
                      )}
                    >
                      {p.nb_alertes_stock} alertes stock
                    </span>
                    <span>{p.nb_tableaux} tableaux</span>
                  </div>
                </div>
                {hasBlockers && (
                  <AlertTriangle
                    size={14}
                    className="text-vinci-red shrink-0"
                  />
                )}
                <ChevronRight
                  size={18}
                  className="text-text-tertiary shrink-0"
                />
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Panneau resume ecarts bloquants : depliable depuis la carte projet
// ---------------------------------------------------------------------------

function BlockingGapsPanel({
  projectId,
  projectCode,
  onClose,
}: {
  projectId: string;
  projectCode: string;
  onClose: () => void;
}) {
  const navigate = useNavigate();

  const { data: runs, isLoading: runsLoading, isError: runsError } = useQuery({
    queryKey: ["dashboard-runs", projectId],
    queryFn: () => listVerificationRuns(projectId),
    staleTime: 30_000,
  });

  const latestRun = useMemo(() => {
    if (!runs || runs.length === 0) return null;
    return [...runs].sort(
      (a, b) => Date.parse(b.created_at) - Date.parse(a.created_at)
    )[0];
  }, [runs]);

  const {
    data: gaps,
    isLoading: gapsLoading,
    isError: gapsError,
  } = useQuery({
    queryKey: ["dashboard-blocking-gaps", projectId, latestRun?.id],
    queryFn: () =>
      listGaps(projectId, latestRun!.id, { severity: "BLOQUANT" }),
    enabled: !!latestRun?.id,
    staleTime: 30_000,
  });

  const openGaps: Gap[] = useMemo(
    () => (gaps ?? []).filter((g) => g.status !== "clos"),
    [gaps]
  );

  const isLoading = runsLoading || (latestRun && gapsLoading);
  const isError = runsError || gapsError;

  return (
    <div className="bg-white border border-vinci-red/40 rounded-lg overflow-hidden shadow-sm">
      <div className="px-4 py-2.5 border-b border-border-std bg-vinci-red/5 flex items-center justify-between">
        <div className="flex items-center gap-2 text-vinci-red">
          <ShieldAlert size={14} />
          <span className="text-sm font-semibold">
            Resume ecarts bloquants : {projectCode}
          </span>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Fermer le resume ecarts bloquants"
          className="text-text-tertiary hover:text-text-primary"
        >
          <X size={16} />
        </button>
      </div>
      <div className="px-4 py-3">
        {isLoading ? (
          <p className="text-xs text-text-tertiary">
            Chargement des ecarts bloquants...
          </p>
        ) : isError ? (
          <p className="text-xs text-status-warn">
            Impossible de charger les ecarts bloquants.
          </p>
        ) : !latestRun ? (
          <p className="text-xs text-text-secondary">
            Aucune verification lancee sur ce projet. Lancez une verification
            depuis l'onglet Verifications.
          </p>
        ) : openGaps.length === 0 ? (
          <p className="text-xs text-text-secondary">
            Aucun ecart bloquant ouvert sur la derniere verification.
          </p>
        ) : (
          <>
            <div className="mb-3 rounded bg-vinci-red/5 border border-vinci-red/20 px-3 py-2 flex flex-wrap items-baseline gap-x-4 gap-y-1">
              <div>
                <span className="text-[10px] uppercase tracking-wide text-text-tertiary">
                  Ecarts bloquants ouverts
                </span>
                <span className="ml-2 text-sm font-semibold text-vinci-red tabular-nums">
                  {openGaps.length}
                </span>
              </div>
              <div>
                <span className="text-[10px] uppercase tracking-wide text-text-tertiary">
                  Derniere verification
                </span>
                <span className="ml-2 text-xs text-text-secondary">
                  {new Date(latestRun.created_at ?? "").toLocaleString("fr-FR")}
                </span>
              </div>
            </div>
            <ul className="space-y-2">
              {openGaps.slice(0, 8).map((g) => (
                <li
                  key={g.id}
                  className="text-xs text-text-secondary leading-relaxed"
                >
                  <div className="flex items-baseline gap-2 flex-wrap">
                    <span className="text-[10px] uppercase tracking-wide text-vinci-red font-semibold">
                      {g.code}
                    </span>
                    <span className="font-semibold text-vinci-blue">
                      {g.title}
                    </span>
                    {g.caneco_repere && (
                      <span className="text-[10px] text-text-tertiary">
                        Repere {g.caneco_repere}
                      </span>
                    )}
                  </div>
                  {g.description && (
                    <p className="mt-0.5 text-text-secondary">
                      {g.description}
                    </p>
                  )}
                  {g.suggested_action && (
                    <p className="mt-0.5 text-[11px] italic text-text-tertiary">
                      Action suggeree : {g.suggested_action}
                    </p>
                  )}
                </li>
              ))}
            </ul>
            {openGaps.length > 8 && (
              <p className="mt-2 text-[11px] text-text-tertiary">
                ... et {openGaps.length - 8} autres bloquants. Voir le detail.
              </p>
            )}
          </>
        )}
      </div>
      <div className="px-4 py-2 border-t border-border-std bg-bg-cell/40 flex justify-end">
        <button
          type="button"
          onClick={() =>
            navigate(`/projects/${projectId}?tab=verifications`)
          }
          className="inline-flex items-center gap-1 text-xs font-medium text-vinci-blue hover:underline"
        >
          Voir le detail
          <ArrowUpRight size={12} />
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Panneau resume alertes stock : depliable depuis la carte projet
// ---------------------------------------------------------------------------

function StockAlertsPanel({
  projectId,
  projectCode,
  onClose,
}: {
  projectId: string;
  projectCode: string;
  onClose: () => void;
}) {
  const navigate = useNavigate();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["dashboard-stock-alerts", projectId],
    queryFn: () => getCableStock(projectId),
    staleTime: 30_000,
  });

  const alerts: CableStockItemRow[] = useMemo(
    () => (data?.items ?? []).filter((it) => it.en_alerte),
    [data]
  );

  // Total a approvisionner = somme des mettres manquants pour repasser
  // au-dessus du seuil d'alerte sur chaque reference concernee.
  const totalAApprovisionner = useMemo(
    () =>
      alerts.reduce(
        (acc, it) => acc + Math.max(it.seuil_alerte_min_m - it.stock_restant, 0),
        0
      ),
    [alerts]
  );

  return (
    <div className="bg-white border border-vinci-red/40 rounded-lg overflow-hidden shadow-sm">
      <div className="px-4 py-2.5 border-b border-border-std bg-vinci-red/5 flex items-center justify-between">
        <div className="flex items-center gap-2 text-vinci-red">
          <Boxes size={14} />
          <span className="text-sm font-semibold">
            Resume alertes stock : {projectCode}
          </span>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Fermer le resume alertes stock"
          className="text-text-tertiary hover:text-text-primary"
        >
          <X size={16} />
        </button>
      </div>
      <div className="px-4 py-3">
        {isLoading ? (
          <p className="text-xs text-text-tertiary">
            Chargement des alertes stock...
          </p>
        ) : isError ? (
          <p className="text-xs text-status-warn">
            Impossible de charger les alertes stock.
          </p>
        ) : alerts.length === 0 ? (
          <p className="text-xs text-text-secondary">
            Aucune reference en alerte sur ce projet.
          </p>
        ) : (
          <>
            <div className="mb-3 rounded bg-vinci-red/5 border border-vinci-red/20 px-3 py-2 flex flex-wrap items-baseline gap-x-4 gap-y-1">
              <div>
                <span className="text-[10px] uppercase tracking-wide text-text-tertiary">
                  References en alerte
                </span>
                <span className="ml-2 text-sm font-semibold text-text-primary tabular-nums">
                  {alerts.length}
                </span>
              </div>
              <div>
                <span className="text-[10px] uppercase tracking-wide text-text-tertiary">
                  A approvisionner pour repasser au-dessus du seuil
                </span>
                <span className="ml-2 text-sm font-semibold text-vinci-red tabular-nums">
                  {formatMeters(totalAApprovisionner)} m
                </span>
              </div>
            </div>
          <ul className="space-y-2">
            {alerts.map((it, idx) => (
              <li
                key={(it.item_id ?? `${it.type_cable}-${it.section_label}-${it.ame}`) + idx}
                className="text-xs text-text-secondary leading-relaxed"
              >
                <span className="font-semibold text-vinci-blue">
                  {it.type_cable} {it.section_label}{" "}
                  <span className="text-text-tertiary font-normal">
                    ({it.ame})
                  </span>
                </span>
                {" : "}
                {it.stock_restant <= 0 ? (
                  <span className="text-vinci-red font-medium">
                    deficit de {formatMeters(Math.abs(it.stock_restant))} m,
                    achat a prevoir
                  </span>
                ) : (
                  <span>
                    il reste{" "}
                    <span className="font-semibold text-text-primary tabular-nums">
                      {formatMeters(it.stock_restant)} m
                    </span>{" "}
                    sous le seuil d'alerte de{" "}
                    {formatMeters(it.seuil_alerte_min_m)} m
                  </span>
                )}
                <span className="block text-[10px] text-text-tertiary mt-0.5">
                  Achete {formatMeters(it.quantite_achetee)} m · Livre{" "}
                  {formatMeters(it.quantite_livree)} m · Utilise{" "}
                  {formatMeters(it.quantite_utilisee)} m
                </span>
              </li>
            ))}
          </ul>
          </>
        )}
      </div>
      <div className="px-4 py-2 border-t border-border-std bg-bg-cell/40 flex justify-end">
        <button
          type="button"
          onClick={() => navigate(`/projects/${projectId}?tab=stock-cables`)}
          className="inline-flex items-center gap-1 text-xs font-medium text-vinci-blue hover:underline"
        >
          Voir le detail
          <ArrowUpRight size={12} />
        </button>
      </div>
    </div>
  );
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

