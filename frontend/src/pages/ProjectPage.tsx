import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  ChevronFirst,
  ChevronLast,
  ChevronLeft,
  ChevronRight,
  Download,
  ExternalLink,
  FileSpreadsheet,
  FileText,
  Info,
  Link2,
  Loader2,
  Pencil,
  Play,
  Printer,
  QrCode,
  RefreshCw,
  Search,
  ShieldAlert,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  deleteCaneco,
  downloadCanecoExcel,
  getCaneco,
  listCaneco,
  updateCanecoIndice,
  uploadCaneco,
} from "@/api/caneco";
import {
  deleteBordereau,
  getBordereau,
  listBordereau,
  previewBordereauSheets,
  updateBordereauIndice,
  uploadBordereau,
} from "@/api/bordereau";
import { downloadCableBookExcel, getCableBook } from "@/api/cable_book";
import {
  downloadFichePdf,
  downloadLabelsPdf,
  fetchTableauQrObjectUrl,
  generateTableaux,
  listTableaux,
  publicFicheUrl,
} from "@/api/tableaux";
import { deleteCpsImport, getCpsImport, listCpsImports, uploadCps } from "@/api/cps";
import { deleteProject, getProject, updateProject } from "@/api/projects";
import {
  createVerificationRun,
  deleteVerificationRun,
  listVerificationRuns,
  getVerificationRun,
  updateGapStatus,
} from "@/api/verification";
import { cn } from "@/lib/utils";
import type {
  BordereauDetail,
  BordereauImport,
  BordereauSection,
  BordereauSheetPreview,
  CableBookEntry,
  CanecoExport,
  CanecoExportDetail,
  CanecoLine,
  CpsImport,
  CpsRule,
  Gap,
  GapSeverity,
  GapStatus,
  ProjectUpdate,
  Tableau,
  VerificationRun,
  VerificationRunDetail,
} from "@/types";

// ---------------------------------------------------------------------------
// Constantes tableau
// ---------------------------------------------------------------------------

const PAGE_SIZES = [25, 50, 100, 200] as const;
type PageSize = (typeof PAGE_SIZES)[number];

type ColDef = {
  key: keyof CanecoLine;
  label: string;
  numeric?: boolean;
  width?: string;
};

const COLUMNS: ColDef[] = [
  { key: "amont", label: "Amont", width: "min-w-[100px]" },
  { key: "repere_aval", label: "Repere aval", width: "min-w-[110px]" },
  { key: "repere", label: "Repere", width: "min-w-[100px]" },
  { key: "designation", label: "Designation", width: "min-w-[180px]" },
  { key: "style", label: "Style", width: "min-w-[90px]" },
  { key: "nb_recepteurs", label: "Nb rec.", numeric: true, width: "min-w-[70px]" },
  { key: "consommation", label: "Conso.", width: "min-w-[90px]" },
  { key: "ib", label: "Ib (A)", numeric: true, width: "min-w-[70px]" },
  { key: "longueur", label: "Long. (m)", numeric: true, width: "min-w-[80px]" },
  { key: "type_cable", label: "Type cable", width: "min-w-[100px]" },
  { key: "nb_cables_multi", label: "Multi", numeric: true, width: "min-w-[60px]" },
  { key: "cable", label: "Section", width: "min-w-[90px]" },
  { key: "neutre", label: "Neutre", width: "min-w-[80px]" },
  { key: "pe", label: "PE/PEN", width: "min-w-[80px]" },
  { key: "calibre", label: "Calibre", numeric: true, width: "min-w-[72px]" },
  { key: "bloc_coupure", label: "Bloc coup.", width: "min-w-[100px]" },
  { key: "bloc_declencheur", label: "Declench.", width: "min-w-[100px]" },
  { key: "bloc_differentiel", label: "Diff.", width: "min-w-[80px]" },
  { key: "ir_th_in", label: "IrTh/IN", numeric: true, width: "min-w-[72px]" },
  { key: "ir_mg_in", label: "IrMg/IN", numeric: true, width: "min-w-[72px]" },
  { key: "icu", label: "Icu (kA)", numeric: true, width: "min-w-[72px]" },
  { key: "contacteur", label: "Contacteur", width: "min-w-[100px]" },
  { key: "ame", label: "Ame", width: "min-w-[60px]" },
];

// ---------------------------------------------------------------------------
// Utilitaires
// ---------------------------------------------------------------------------

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("fr-FR", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });
}

function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatNum(n: number): string {
  if (Number.isInteger(n)) return String(n);
  return n.toLocaleString("fr-FR", { maximumFractionDigits: 3 });
}

function detectIndiceFromFilename(filename: string): string | null {
  const m = filename.toUpperCase().match(/INDICE[_\s]+([A-Z][0-9]*)/);
  if (m) return m[1];
  const m2 = filename.toUpperCase().match(/[_\s]([A-Z])\./);
  if (m2) return m2[1];
  return null;
}

function isRawOnly(line: CanecoLine, fieldKey: keyof CanecoLine): boolean {
  const value = line[fieldKey];
  if (value !== null && value !== undefined) return false;
  const rawVal = line.raw_data?.[fieldKey as string];
  return !!rawVal && rawVal.trim() !== "";
}

function getRawValue(line: CanecoLine, fieldKey: keyof CanecoLine): string {
  return line.raw_data?.[fieldKey as string] ?? "";
}

// ---------------------------------------------------------------------------
// Onglets
// ---------------------------------------------------------------------------

const TABS = [
  { id: "overview", label: "Vue d'ensemble" },
  { id: "studies", label: "Etudes" },
  { id: "bordereau", label: "Bordereau" },
  { id: "cps", label: "CPS" },
  { id: "verifications", label: "Verifications" },
  { id: "cable-book", label: "Carnet cables" },
  { id: "tableaux", label: "Tableaux" },
  { id: "doe", label: "DOE" },
] as const;

type TabId = (typeof TABS)[number]["id"];

const STATUS_OPTIONS = ["actif", "en_attente", "archive"];

const DOMAINE_LABELS: Record<string, string> = {
  habitation: "Habitation (résidentiel)",
  tertiaire: "Tertiaire (bureaux, logistique)",
  industriel: "Industriel",
  erp: "ERP (recevant du public)",
};

// ---------------------------------------------------------------------------
// Composant principal
// ---------------------------------------------------------------------------

export default function ProjectPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<TabId>("overview");
  const [showEdit, setShowEdit] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [editData, setEditData] = useState<ProjectUpdate>({});
  const [editError, setEditError] = useState<string | null>(null);

  const { data: project, isLoading, isError } = useQuery({
    queryKey: ["project", id],
    queryFn: () => getProject(id!),
    enabled: !!id,
  });

  const { mutate: doUpdate, isPending: isUpdating } = useMutation({
    mutationFn: (payload: ProjectUpdate) => updateProject(id!, payload),
    onSuccess: (updated) => {
      queryClient.setQueryData(["project", id], updated);
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setShowEdit(false);
      setEditError(null);
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Erreur lors de la mise a jour.";
      setEditError(msg);
    },
  });

  const { mutate: doDelete, isPending: isDeleting } = useMutation({
    mutationFn: () => deleteProject(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      navigate("/projects");
    },
  });

  function openEdit() {
    if (!project) return;
    setEditData({
      name: project.name,
      client: project.client ?? "",
      agency: project.agency ?? "",
      description: project.description ?? "",
      status: project.status,
      domaine_installation: project.domaine_installation,
    });
    setEditError(null);
    setShowEdit(true);
  }

  function handleUpdate(e: React.FormEvent) {
    e.preventDefault();
    if (!editData.name?.trim()) {
      setEditError("Le nom est obligatoire.");
      return;
    }
    doUpdate(editData);
  }

  if (isLoading) {
    return <div className="p-6 text-sm text-text-tertiary">Chargement...</div>;
  }

  if (isError || !project) {
    return <div className="p-6 text-sm text-status-warn">Projet introuvable.</div>;
  }

  return (
    <div className="flex-1 min-h-0 flex flex-col">
      {/* En-tete projet — compact, epingle */}
      <div className="shrink-0 px-6 py-2 border-b border-border-std bg-white">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <button
              onClick={() => navigate("/projects")}
              className="flex items-center gap-1 text-xs text-text-tertiary hover:text-text-primary transition-colors shrink-0"
            >
              <ChevronLeft size={13} />
              Projets
            </button>
            <span className="text-text-tertiary text-xs">/</span>
            <span className="text-xs font-mono text-text-tertiary shrink-0">{project.code}</span>
            <h2 className="text-sm font-semibold text-text-primary truncate">{project.name}</h2>
            {project.client && (
              <span className="text-xs text-text-tertiary truncate hidden sm:block">{project.client}</span>
            )}
            <span
              className={cn(
                "text-xs px-2 py-0.5 rounded shrink-0",
                project.status === "actif" && "bg-green-100 text-status-ok",
                project.status === "archive" && "bg-gray-100 text-text-tertiary",
                project.status === "en_attente" && "bg-yellow-100 text-yellow-700",
                !["actif", "archive", "en_attente"].includes(project.status) &&
                  "bg-bg-cell text-text-tertiary"
              )}
            >
              {project.status}
            </span>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={openEdit}
              title="Modifier le projet"
              className="flex items-center gap-1 px-2 py-1 text-xs border border-border-std rounded hover:bg-bg-cell transition-colors text-text-secondary"
            >
              <Pencil size={12} />
              Modifier
            </button>
            <button
              onClick={() => setShowDeleteConfirm(true)}
              title="Supprimer le projet"
              className="flex items-center gap-1 px-2 py-1 text-xs border border-red-200 rounded hover:bg-red-50 transition-colors text-status-warn"
            >
              <Trash2 size={12} />
            </button>
          </div>
        </div>
      </div>

      {/* Onglets — epingles, ne scrollent jamais */}
      <div className="shrink-0 border-b border-border-std bg-white px-6">
        <div className="flex gap-0">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "px-4 py-3 text-sm border-b-2 transition-colors",
                activeTab === tab.id
                  ? "border-vinci-blue text-vinci-blue font-medium"
                  : "border-transparent text-text-secondary hover:text-text-primary"
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Contenu onglets — zone de defilement independante par onglet */}
      <div className="flex-1 min-h-0 overflow-hidden flex flex-col">
        {activeTab === "overview" && (
          <div className="flex-1 min-h-0 overflow-auto p-6">
            <div className="max-w-lg space-y-4">
              <div className="bg-white border border-border-std rounded p-4">
                <h3 className="text-xs font-semibold text-text-tertiary uppercase tracking-wide mb-3">
                  Informations projet
                </h3>
                <dl className="space-y-2.5 text-sm">
                  <Row label="Code" value={<span className="font-mono">{project.code}</span>} />
                  <Row label="Nom" value={project.name} />
                  {project.client && <Row label="Client" value={project.client} />}
                  {project.agency && <Row label="Agence" value={project.agency} />}
                  {project.description && <Row label="Description" value={project.description} />}
                  <Row label="Statut" value={project.status} />
                  <Row
                    label="Domaine"
                    value={DOMAINE_LABELS[project.domaine_installation] ?? project.domaine_installation}
                  />
                </dl>
              </div>

              <div className="bg-white border border-border-std rounded p-4">
                <h3 className="text-xs font-semibold text-text-tertiary uppercase tracking-wide mb-3">
                  Historique
                </h3>
                <dl className="space-y-2.5 text-sm">
                  <Row label="Cree le" value={formatDate(project.created_at)} />
                  <Row label="Modifie le" value={formatDate(project.updated_at)} />
                </dl>
              </div>
            </div>
          </div>
        )}

        {activeTab === "studies" && <EtudesTab projectId={id!} />}

        {activeTab === "bordereau" && <BordereauTab projectId={id!} />}

        {activeTab === "cps" && <CpsTab projectId={id!} />}

        {activeTab === "verifications" && <VerificationsTab projectId={id!} />}

        {activeTab === "cable-book" && <CableBookTab projectId={id!} />}

        {activeTab === "tableaux" && <TableauxTab projectId={id!} />}
        {activeTab === "doe" && (
          <div className="flex-1 min-h-0 overflow-auto p-6">
            <div className="text-sm text-text-tertiary">
              Module 5 — Generation DOE (disponible en V1.1)
            </div>
          </div>
        )}
      </div>

      {/* Modal modifier projet */}
      {showEdit && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded w-full max-w-md shadow-lg">
            <div className="flex items-center justify-between px-5 py-4 border-b border-border-std">
              <h3 className="font-semibold text-text-primary">Modifier le projet</h3>
              <button
                onClick={() => setShowEdit(false)}
                className="text-text-tertiary hover:text-text-primary"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleUpdate} className="p-5 space-y-4">
              <div>
                <label className="block text-sm text-text-secondary mb-1">
                  Nom <span className="text-status-warn">*</span>
                </label>
                <input
                  type="text"
                  value={editData.name ?? ""}
                  onChange={(e) => setEditData((d) => ({ ...d, name: e.target.value }))}
                  className="w-full border border-border-std rounded px-3 py-2 text-sm focus:outline-none focus:border-vinci-blue"
                />
              </div>

              <div>
                <label className="block text-sm text-text-secondary mb-1">Client</label>
                <input
                  type="text"
                  value={editData.client ?? ""}
                  onChange={(e) => setEditData((d) => ({ ...d, client: e.target.value }))}
                  className="w-full border border-border-std rounded px-3 py-2 text-sm focus:outline-none focus:border-vinci-blue"
                />
              </div>

              <div>
                <label className="block text-sm text-text-secondary mb-1">Agence</label>
                <input
                  type="text"
                  value={editData.agency ?? ""}
                  onChange={(e) => setEditData((d) => ({ ...d, agency: e.target.value }))}
                  className="w-full border border-border-std rounded px-3 py-2 text-sm focus:outline-none focus:border-vinci-blue"
                />
              </div>

              <div>
                <label className="block text-sm text-text-secondary mb-1">Description</label>
                <textarea
                  rows={3}
                  value={editData.description ?? ""}
                  onChange={(e) => setEditData((d) => ({ ...d, description: e.target.value }))}
                  className="w-full border border-border-std rounded px-3 py-2 text-sm focus:outline-none focus:border-vinci-blue resize-none"
                />
              </div>

              <div>
                <label className="block text-sm text-text-secondary mb-1">Statut</label>
                <select
                  value={editData.status ?? "actif"}
                  onChange={(e) => setEditData((d) => ({ ...d, status: e.target.value }))}
                  className="w-full border border-border-std rounded px-3 py-2 text-sm focus:outline-none focus:border-vinci-blue bg-white"
                >
                  {STATUS_OPTIONS.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm text-text-secondary mb-1">
                  Domaine d'installation
                </label>
                <select
                  value={editData.domaine_installation ?? project?.domaine_installation ?? "tertiaire"}
                  onChange={(e) =>
                    setEditData((d) => ({
                      ...d,
                      domaine_installation: e.target.value as
                        | "habitation"
                        | "tertiaire"
                        | "industriel"
                        | "erp",
                    }))
                  }
                  className="w-full border border-border-std rounded px-3 py-2 text-sm focus:outline-none focus:border-vinci-blue bg-white"
                >
                  <option value="tertiaire">Tertiaire (bureaux, logistique)</option>
                  <option value="habitation">Habitation (résidentiel)</option>
                  <option value="industriel">Industriel</option>
                  <option value="erp">ERP (recevant du public)</option>
                </select>
                <p className="mt-1 text-xs text-text-tertiary">
                  Conditionne les règles NF C 15-100 (ex. DDR 30 mA prises = habitation uniquement).
                </p>
              </div>

              {editError && <p className="text-xs text-status-warn">{editError}</p>}

              <div className="flex gap-3 justify-end pt-2">
                <button
                  type="button"
                  onClick={() => setShowEdit(false)}
                  className="px-4 py-2 text-sm text-text-secondary border border-border-std rounded hover:bg-bg-cell transition-colors"
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  disabled={isUpdating}
                  className="px-4 py-2 text-sm bg-vinci-blue text-white rounded hover:bg-vinci-blue/90 transition-colors disabled:opacity-50"
                >
                  {isUpdating ? "Enregistrement..." : "Enregistrer"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal confirmation suppression projet */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded w-full max-w-sm shadow-lg p-6">
            <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center mb-4">
              <Trash2 size={18} className="text-status-warn" />
            </div>
            <h3 className="font-semibold text-text-primary mb-2">Supprimer le projet</h3>
            <p className="text-sm text-text-secondary mb-1">
              Vous etes sur le point de supprimer{" "}
              <span className="font-medium text-text-primary">{project.name}</span>.
            </p>
            <p className="text-xs text-text-tertiary mb-6">
              Cette action est irreversible. Toutes les donnees associees seront perdues.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                disabled={isDeleting}
                className="px-4 py-2 text-sm text-text-secondary border border-border-std rounded hover:bg-bg-cell transition-colors"
              >
                Annuler
              </button>
              <button
                onClick={() => doDelete()}
                disabled={isDeleting}
                className="px-4 py-2 text-sm bg-red-600 text-white rounded hover:bg-red-700 transition-colors disabled:opacity-50"
              >
                {isDeleting ? "Suppression..." : "Supprimer definitivement"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Onglet Etudes
// ---------------------------------------------------------------------------

function EtudesTab({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const [selectedExportId, setSelectedExportId] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState<PageSize>(50);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [showUpload, setShowUpload] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [editIndiceId, setEditIndiceId] = useState<string | null>(null);

  const { data: exports, isLoading: loadingExports } = useQuery({
    queryKey: ["caneco", projectId],
    queryFn: () => listCaneco(projectId),
  });

  const { data: detail, isLoading: loadingDetail } = useQuery({
    queryKey: ["caneco-detail", projectId, selectedExportId, page, perPage, search],
    queryFn: () => getCaneco(projectId, selectedExportId!, page, perPage, search),
    enabled: !!selectedExportId,
  });

  const { mutate: doDeleteExport, isPending: isDeleting } = useMutation({
    mutationFn: (exportId: string) => deleteCaneco(projectId, exportId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["caneco", projectId] });
      if (confirmDeleteId === selectedExportId) {
        setSelectedExportId(null);
      }
      setConfirmDeleteId(null);
    },
  });

  const { mutate: doUpdateIndice } = useMutation({
    mutationFn: ({ exportId, indice }: { exportId: string; indice: string }) =>
      updateCanecoIndice(projectId, exportId, indice),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["caneco", projectId] });
      setEditIndiceId(null);
    },
  });

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setSearch(searchInput);
    setPage(1);
  }

  function handleClearSearch() {
    setSearchInput("");
    setSearch("");
    setPage(1);
  }

  function handleSelectExport(exp: CanecoExport) {
    setSelectedExportId(exp.id);
    setPage(1);
    setSearch("");
    setSearchInput("");
    setShowUpload(false);
  }

  if (loadingExports) {
    return <div className="p-6 text-sm text-text-tertiary">Chargement...</div>;
  }

  const hasExports = exports && exports.length > 0;
  const selectedExport = exports?.find((e) => e.id === selectedExportId) ?? null;
  const hasTable = !!selectedExportId && !!selectedExport;

  return (
    <div className="flex-1 min-h-0 flex flex-col">

      {hasTable ? (
        /* ── MODE TABLEAU OUVERT ─────────────────────────────────────────── */
        <>
          {/* Barre compacte 1 ligne : info fichier + actions */}
          <div className="shrink-0 px-6 py-2 border-b border-border-std bg-white flex items-center justify-between gap-4">
            <div className="flex items-center gap-2 min-w-0 text-xs">
              <button
                onClick={() => setSelectedExportId(null)}
                className="flex items-center gap-1 text-text-tertiary hover:text-vinci-blue transition-colors shrink-0"
              >
                <ChevronLeft size={13} />
                Imports
              </button>
              <span className="text-text-tertiary shrink-0">/</span>
              <span className="font-semibold px-2 py-0.5 rounded bg-vinci-blue text-white shrink-0">
                Indice {selectedExport.indice}
              </span>
              <span className="text-status-ok shrink-0">
                {selectedExport.line_count} lignes
              </span>
              <span className="text-text-tertiary shrink-0">·</span>
              <span className="text-status-ok shrink-0">
                {selectedExport.columns_mapped ?? 0}/{selectedExport.columns_detected ?? 23} col.
              </span>
              <span className="text-text-tertiary shrink-0">·</span>
              <span className="truncate text-text-tertiary">{selectedExport.file_name}</span>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={() => setEditIndiceId(selectedExport.id)}
                className="flex items-center gap-1 px-2 py-1 text-xs border border-border-std rounded hover:bg-bg-cell transition-colors text-text-secondary"
              >
                <Pencil size={11} />
                Indice
              </button>
              <button
                onClick={() => { setShowUpload(true); setSelectedExportId(null); }}
                className="flex items-center gap-1 px-2 py-1 text-xs bg-vinci-blue text-white rounded hover:bg-vinci-blue/90 transition-colors"
              >
                <Upload size={11} />
                Importer
              </button>
            </div>
          </div>

          {/* Tableau — prend toute la hauteur restante */}
          <div className="flex-1 min-h-0 px-6 pb-4 flex flex-col pt-3">
            <LinesTable
              projectId={projectId}
              exportId={selectedExportId}
              selectedExport={selectedExport}
              detail={detail ?? null}
              isLoading={loadingDetail}
              page={page}
              perPage={perPage}
              search={search}
              searchInput={searchInput}
              onPageChange={(p) => setPage(p)}
              onPerPageChange={(pp) => { setPerPage(pp); setPage(1); }}
              onSearchSubmit={handleSearch}
              onSearchInputChange={setSearchInput}
              onClearSearch={handleClearSearch}
            />
          </div>
        </>
      ) : (
        /* ── MODE LISTE DES IMPORTS ──────────────────────────────────────── */
        <div className="flex-1 min-h-0 overflow-auto px-6 pt-4 pb-6 space-y-3">
          {/* Barre d'actions */}
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-text-primary">
              Etudes CANECO BT
              {hasExports && (
                <span className="ml-2 text-xs font-normal text-text-tertiary">
                  {exports.length} import{exports.length > 1 ? "s" : ""}
                </span>
              )}
            </h3>
            <button
              onClick={() => setShowUpload((v) => !v)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-vinci-blue text-white rounded hover:bg-vinci-blue/90 transition-colors"
            >
              <Upload size={13} />
              Importer un fichier CANECO
            </button>
          </div>

          {/* Formulaire upload */}
          {showUpload && (
            <UploadForm
              projectId={projectId}
              onDone={(newExport) => {
                queryClient.invalidateQueries({ queryKey: ["caneco", projectId] });
                setShowUpload(false);
                setSelectedExportId(newExport.id);
                setPage(1);
              }}
              onCancel={() => setShowUpload(false)}
            />
          )}

          {/* Etat vide */}
          {!hasExports && !showUpload && (
            <EmptyState onUpload={() => setShowUpload(true)} />
          )}

          {/* Cartes des imports */}
          {hasExports && (
            <div className="grid grid-cols-1 gap-2">
              {exports.map((exp, idx) => (
                <ExportCard
                  key={exp.id}
                  exp={exp}
                  isFirst={idx === 0}
                  isSelected={false}
                  onSelect={() => handleSelectExport(exp)}
                  onDelete={() => setConfirmDeleteId(exp.id)}
                  onEditIndice={() => setEditIndiceId(exp.id)}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Modal suppression export */}
      {confirmDeleteId && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded w-full max-w-sm shadow-lg p-6">
            <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center mb-4">
              <Trash2 size={18} className="text-status-warn" />
            </div>
            <h3 className="font-semibold text-text-primary mb-2">Supprimer l'import</h3>
            <p className="text-sm text-text-secondary mb-1">
              Cette action supprimera definitivement cet import et toutes ses lignes parsees.
            </p>
            <p className="text-xs text-text-tertiary mb-6">Cette operation est irreversible.</p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setConfirmDeleteId(null)}
                disabled={isDeleting}
                className="px-4 py-2 text-sm text-text-secondary border border-border-std rounded hover:bg-bg-cell transition-colors"
              >
                Annuler
              </button>
              <button
                onClick={() => doDeleteExport(confirmDeleteId)}
                disabled={isDeleting}
                className="px-4 py-2 text-sm bg-red-600 text-white rounded hover:bg-red-700 transition-colors disabled:opacity-50"
              >
                {isDeleting ? "Suppression..." : "Supprimer"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal modification indice */}
      {editIndiceId && (
        <IndiceModal
          currentIndice={exports?.find((e) => e.id === editIndiceId)?.indice ?? ""}
          onSave={(indice) => doUpdateIndice({ exportId: editIndiceId, indice })}
          onClose={() => setEditIndiceId(null)}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Carte export
// ---------------------------------------------------------------------------

function ExportCard({
  exp,
  isFirst,
  isSelected,
  onSelect,
  onDelete,
  onEditIndice,
}: {
  exp: CanecoExport;
  isFirst: boolean;
  isSelected: boolean;
  onSelect: () => void;
  onDelete: () => void;
  onEditIndice: () => void;
}) {
  const statusConfig = {
    parsed: { label: "Parse", cls: "bg-green-100 text-status-ok" },
    parsing: { label: "En cours...", cls: "bg-yellow-100 text-yellow-700" },
    error: { label: "Erreur", cls: "bg-red-100 text-status-warn" },
  } as const;

  const cfg = statusConfig[exp.status] ?? { label: exp.status, cls: "bg-bg-cell text-text-tertiary" };
  const histBadge = isFirst
    ? { label: "actif", cls: "bg-green-100 text-status-ok" }
    : { label: "ancien", cls: "bg-gray-100 text-text-tertiary" };

  const metaLine = exp.status === "parsed" && exp.columns_mapped !== null
    ? `${exp.lines_read ?? 0} lignes lues, ${exp.line_count ?? 0} parsees — ${exp.columns_mapped}/${exp.columns_detected ?? 23} colonnes standard${(exp.extra_columns_count ?? 0) > 0 ? `, ${exp.extra_columns_count} suppl.` : ""}`
    : null;

  return (
    <div
      className={cn(
        "border rounded p-3.5 cursor-pointer transition-colors group",
        isSelected
          ? "border-vinci-blue bg-blue-50/40"
          : "border-border-std bg-white hover:border-vinci-blue/40"
      )}
      onClick={onSelect}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <FileSpreadsheet size={16} className="text-text-tertiary shrink-0" />
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-vinci-blue text-white">
                Indice {exp.indice}
              </span>
              <span className={cn("text-xs px-2 py-0.5 rounded", histBadge.cls)}>
                {histBadge.label}
              </span>
              <span className={cn("text-xs px-2 py-0.5 rounded", cfg.cls)}>{cfg.label}</span>
              {exp.line_count !== null && (
                <span className="text-xs text-text-tertiary">
                  {exp.line_count} ligne{exp.line_count > 1 ? "s" : ""}
                </span>
              )}
            </div>
            <p className="text-xs text-text-tertiary mt-0.5 truncate">{exp.file_name}</p>
            {metaLine && (
              <p className="text-xs text-text-tertiary mt-0.5">{metaLine}</p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <span className="text-xs text-text-tertiary hidden sm:block">
            {formatDateTime(exp.uploaded_at)}
          </span>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onEditIndice();
            }}
            className="opacity-0 group-hover:opacity-100 transition-opacity text-text-tertiary hover:text-vinci-blue"
            title="Modifier l'indice"
          >
            <Pencil size={13} />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="opacity-0 group-hover:opacity-100 transition-opacity text-text-tertiary hover:text-status-warn"
            title="Supprimer cet import"
          >
            <Trash2 size={13} />
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tableau des lignes avec en-tetes epingles
// ---------------------------------------------------------------------------

function LinesTable({
  projectId,
  exportId,
  selectedExport,
  detail,
  isLoading,
  page,
  perPage,
  search,
  searchInput,
  onPageChange,
  onPerPageChange,
  onSearchSubmit,
  onSearchInputChange,
  onClearSearch,
}: {
  projectId: string;
  exportId: string;
  selectedExport: CanecoExport;
  detail: CanecoExportDetail | null;
  isLoading: boolean;
  page: number;
  perPage: PageSize;
  search: string;
  searchInput: string;
  onPageChange: (p: number) => void;
  onPerPageChange: (pp: PageSize) => void;
  onSearchSubmit: (e: React.FormEvent) => void;
  onSearchInputChange: (v: string) => void;
  onClearSearch: () => void;
}) {
  const total = detail?.total ?? 0;
  const total_pages = detail?.total_pages ?? 1;
  const rangeStart = total === 0 ? 0 : (page - 1) * perPage + 1;
  const rangeEnd = Math.min(page * perPage, total);

  return (
    <div className="flex-1 min-h-0 flex flex-col gap-2">
      {/* Barre recherche + pagination — epinglee au-dessus du tableau */}
      <div className="shrink-0 flex flex-wrap items-center justify-between gap-3 bg-white border border-border-std rounded px-3 py-2">
        {/* Recherche */}
        <form onSubmit={onSearchSubmit} className="flex items-center gap-1.5 min-w-0">
          <div className="relative flex items-center">
            <Search size={13} className="absolute left-2 text-text-tertiary pointer-events-none" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => onSearchInputChange(e.target.value)}
              placeholder="Recherche libre..."
              className="pl-7 pr-7 py-1 text-xs border border-border-std rounded focus:outline-none focus:border-vinci-blue w-48"
            />
            {searchInput && (
              <button
                type="button"
                onClick={onClearSearch}
                className="absolute right-2 text-text-tertiary hover:text-text-primary"
              >
                <X size={12} />
              </button>
            )}
          </div>
          <button
            type="submit"
            className="px-2 py-1 text-xs bg-vinci-blue text-white rounded hover:bg-vinci-blue/90 transition-colors"
          >
            Ok
          </button>
          {search && (
            <span className="text-xs text-text-tertiary">
              Filtre : <span className="font-medium text-text-primary">"{search}"</span>
            </span>
          )}
        </form>

        {/* Compteur + pagination */}
        <div className="flex items-center gap-3 shrink-0">
          <span className="text-xs text-text-tertiary">
            {total} ligne{total !== 1 ? "s" : ""} — page {page}/{total_pages} — {rangeStart}–{rangeEnd}
          </span>

          <div className="flex items-center gap-1">
            <label className="text-xs text-text-tertiary">Lignes :</label>
            <select
              value={perPage}
              onChange={(e) => onPerPageChange(Number(e.target.value) as PageSize)}
              className="text-xs border border-border-std rounded px-1 py-0.5 bg-white focus:outline-none focus:border-vinci-blue"
            >
              {PAGE_SIZES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-0.5">
            <PageBtn
              icon={<ChevronFirst size={13} />}
              onClick={() => onPageChange(1)}
              disabled={page <= 1}
              title="Premiere page"
            />
            <PageBtn
              icon={<ChevronLeft size={13} />}
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
              title="Page precedente"
            />
            <PageBtn
              icon={<ChevronRight size={13} />}
              onClick={() => onPageChange(page + 1)}
              disabled={page >= total_pages}
              title="Page suivante"
            />
            <PageBtn
              icon={<ChevronLast size={13} />}
              onClick={() => onPageChange(total_pages)}
              disabled={page >= total_pages}
              title="Derniere page"
            />
          </div>

          <ExcelExportBtn
            projectId={projectId}
            exportId={exportId}
            indice={selectedExport.indice}
          />
        </div>
      </div>

      {/* Conteneur du tableau — defilement independant (X et Y), prend toute la hauteur restante */}
      <div className="flex-1 min-h-0 overflow-auto border border-border-std rounded">
        {isLoading ? (
          <div className="p-8 text-center text-sm text-text-tertiary">
            Chargement des donnees...
          </div>
        ) : !detail || detail.lines.length === 0 ? (
          <div className="p-8 text-center text-sm text-text-tertiary">
            {search ? `Aucun resultat pour "${search}".` : "Aucune ligne."}
          </div>
        ) : (
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr>
                {/* Cellule coin : epinglee en haut ET a gauche (z-index max) */}
                <th
                  className="px-3 py-2 text-left font-medium text-white text-xs whitespace-nowrap border-r border-white/10"
                  style={{
                    background: "#001E50",
                    position: "sticky",
                    top: 0,
                    left: 0,
                    zIndex: 30,
                    minWidth: "48px",
                    boxShadow: "2px 2px 0 rgba(0,0,0,0.08)",
                  }}
                >
                  #
                </th>
                {/* En-tetes colonnes : epingles en haut, defilent horizontalement */}
                {COLUMNS.map((col) => (
                  <th
                    key={col.key}
                    className={cn(
                      "px-3 py-2 text-left font-medium text-white text-xs whitespace-nowrap border-r border-white/10 last:border-r-0",
                      col.width
                    )}
                    style={{
                      background: "#001E50",
                      position: "sticky",
                      top: 0,
                      zIndex: 20,
                      boxShadow: "0 2px 0 rgba(0,0,0,0.08)",
                    }}
                  >
                    {col.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {detail.lines.map((line, rowIdx) => (
                <tr
                  key={line.id}
                  className={cn(
                    "border-b border-slate-200 hover:bg-blue-50/40 transition-colors",
                    rowIdx % 2 === 0 ? "bg-white" : "bg-slate-50"
                  )}
                >
                  {/* Cellule # : epinglee a gauche dans le corps */}
                  <td
                    className={cn(
                      "px-3 py-1.5 font-mono text-text-tertiary border-r border-slate-200",
                      rowIdx % 2 === 0 ? "bg-white" : "bg-slate-50"
                    )}
                    style={{ position: "sticky", left: 0, zIndex: 10 }}
                  >
                    {line.excel_row_number ?? line.row_index + 2}
                  </td>

                  {COLUMNS.map((col) => (
                    <DataCell key={col.key} line={line} col={col} />
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination basse — taille fixe */}
      {detail && total_pages > 1 && (
        <div className="shrink-0 flex justify-center items-center gap-1">
          <PageBtn
            icon={<ChevronFirst size={13} />}
            onClick={() => onPageChange(1)}
            disabled={page <= 1}
            title="Premiere page"
          />
          <PageBtn
            icon={<ChevronLeft size={13} />}
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            title="Page precedente"
          />
          <span className="text-xs text-text-tertiary px-2">
            {page} / {total_pages}
          </span>
          <PageBtn
            icon={<ChevronRight size={13} />}
            onClick={() => onPageChange(page + 1)}
            disabled={page >= total_pages}
            title="Page suivante"
          />
          <PageBtn
            icon={<ChevronLast size={13} />}
            onClick={() => onPageChange(total_pages)}
            disabled={page >= total_pages}
            title="Derniere page"
          />
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Cellule de donnee avec indicateur valeur brute non normalisee
// ---------------------------------------------------------------------------

function DataCell({ line, col }: { line: CanecoLine; col: ColDef }) {
  const value = line[col.key];
  const rawOnly = isRawOnly(line, col.key);
  const rawVal = rawOnly ? getRawValue(line, col.key) : "";

  if (rawOnly) {
    return (
      <td
        className="px-3 py-1.5 whitespace-nowrap border-l-2 border-l-red-400"
        title="Valeur brute non normalisee"
      >
        <span className="italic text-text-tertiary">{rawVal}</span>
      </td>
    );
  }

  if (value === null || value === undefined) {
    return (
      <td className="px-3 py-1.5 whitespace-nowrap">
        <span className="text-slate-300">—</span>
      </td>
    );
  }

  return (
    <td
      className={cn(
        "px-3 py-1.5 whitespace-nowrap text-text-primary",
        col.numeric && "font-mono"
      )}
    >
      {typeof value === "number" ? formatNum(value) : String(value)}
    </td>
  );
}

// ---------------------------------------------------------------------------
// Bouton export Excel
// ---------------------------------------------------------------------------

function ExcelExportBtn({
  projectId,
  exportId,
  indice,
}: {
  projectId: string;
  exportId: string;
  indice: string;
}) {
  const { mutate, isPending } = useMutation({
    mutationFn: () => downloadCanecoExcel(projectId, exportId, indice),
  });

  return (
    <button
      onClick={() => mutate()}
      disabled={isPending}
      className="flex items-center gap-1 px-2 py-1 text-xs border border-border-std rounded hover:bg-bg-cell transition-colors text-text-secondary disabled:opacity-50"
      title="Exporter en Excel"
    >
      <Download size={12} />
      {isPending ? "..." : "Excel"}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Bouton de pagination
// ---------------------------------------------------------------------------

function PageBtn({
  icon,
  onClick,
  disabled,
  title,
}: {
  icon: React.ReactNode;
  onClick: () => void;
  disabled: boolean;
  title: string;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className="p-1 rounded border border-border-std hover:bg-bg-cell disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
    >
      {icon}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Modal modification indice
// ---------------------------------------------------------------------------

function IndiceModal({
  currentIndice,
  onSave,
  onClose,
}: {
  currentIndice: string;
  onSave: (indice: string) => void;
  onClose: () => void;
}) {
  const [value, setValue] = useState(currentIndice);

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded w-full max-w-xs shadow-lg p-5">
        <h3 className="font-semibold text-text-primary mb-3">Modifier l'indice</h3>
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value.toUpperCase())}
          maxLength={10}
          placeholder="ex. A, B, B2, C..."
          className="w-full border border-border-std rounded px-3 py-2 text-sm font-mono uppercase focus:outline-none focus:border-vinci-blue mb-4"
          autoFocus
        />
        <div className="flex gap-3 justify-end">
          <button
            onClick={onClose}
            className="px-3 py-2 text-sm text-text-secondary border border-border-std rounded hover:bg-bg-cell transition-colors"
          >
            Annuler
          </button>
          <button
            onClick={() => { if (value.trim()) onSave(value.trim()); }}
            disabled={!value.trim()}
            className="px-3 py-2 text-sm bg-vinci-blue text-white rounded hover:bg-vinci-blue/90 transition-colors disabled:opacity-50"
          >
            Enregistrer
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Formulaire d'upload
// ---------------------------------------------------------------------------

function UploadForm({
  projectId,
  onDone,
  onCancel,
}: {
  projectId: string;
  onDone: (exp: CanecoExport) => void;
  onCancel: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [indice, setIndice] = useState("A");
  const [indiceDetected, setIndiceDetected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const { mutate: doUpload, isPending } = useMutation({
    mutationFn: () => uploadCaneco(projectId, file!, indice),
    onSuccess: (exp) => onDone(exp),
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Erreur lors de l'import.";
      setError(msg);
    },
  });

  const handleFile = useCallback((f: File) => {
    const ext = f.name.split(".").pop()?.toLowerCase();
    if (!["xls", "xlsx"].includes(ext ?? "")) {
      setError("Format non supporte. Utilisez un fichier .xls ou .xlsx.");
      return;
    }
    if (f.size > 50 * 1024 * 1024) {
      setError("Fichier trop volumineux (max 50 Mo).");
      return;
    }
    setFile(f);
    setError(null);
    const detected = detectIndiceFromFilename(f.name);
    if (detected) {
      setIndice(detected);
      setIndiceDetected(true);
    } else {
      setIndiceDetected(false);
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const f = e.dataTransfer.files[0];
      if (f) handleFile(f);
    },
    [handleFile]
  );

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) {
      setError("Veuillez selectionner un fichier.");
      return;
    }
    if (!indice.trim()) {
      setError("L'indice est obligatoire.");
      return;
    }
    setError(null);
    doUpload();
  }

  return (
    <div className="border border-border-std rounded bg-white p-5">
      <h4 className="text-sm font-semibold text-text-primary mb-4">
        Importer un export CANECO BT
      </h4>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          className={cn(
            "border-2 border-dashed rounded p-8 text-center cursor-pointer transition-colors",
            isDragging
              ? "border-vinci-blue bg-blue-50"
              : file
              ? "border-green-400 bg-green-50"
              : "border-border-std hover:border-vinci-blue/50 hover:bg-bg-light"
          )}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".xls,.xlsx"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleFile(f);
            }}
          />
          <FileSpreadsheet
            size={32}
            className={cn("mx-auto mb-2", file ? "text-green-600" : "text-text-tertiary")}
          />
          {file ? (
            <div>
              <p className="text-sm font-medium text-text-primary">{file.name}</p>
              <p className="text-xs text-text-tertiary mt-1">
                {(file.size / 1024).toFixed(0)} Ko — cliquez pour changer
              </p>
            </div>
          ) : (
            <div>
              <p className="text-sm text-text-secondary">Glissez votre fichier XLS/XLSX ici</p>
              <p className="text-xs text-text-tertiary mt-1">ou cliquez pour parcourir</p>
            </div>
          )}
        </div>

        <div className="flex items-center gap-3">
          <label className="text-sm text-text-secondary shrink-0 w-32">
            Indice de revision
          </label>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={indice}
              onChange={(e) => { setIndice(e.target.value.toUpperCase()); setIndiceDetected(false); }}
              maxLength={10}
              placeholder="A"
              className={cn(
                "w-24 border rounded px-3 py-2 text-sm font-mono uppercase focus:outline-none",
                indiceDetected
                  ? "border-green-400 focus:border-green-500"
                  : "border-border-std focus:border-vinci-blue"
              )}
            />
            {file && !indice.trim() && (
              <span className="text-xs text-orange-600">Indice non detecte — saisir manuellement</span>
            )}
            {indiceDetected && (
              <span className="text-xs text-status-ok">Detecte depuis le nom du fichier</span>
            )}
          </div>
        </div>

        {error && (
          <div className="flex items-start gap-2 text-xs text-status-warn bg-red-50 border border-red-200 rounded px-3 py-2">
            <span className="mt-0.5 shrink-0">&#9888;</span>
            <span>{error}</span>
          </div>
        )}

        <div className="flex gap-3 justify-end">
          <button
            type="button"
            onClick={onCancel}
            disabled={isPending}
            className="px-4 py-2 text-sm text-text-secondary border border-border-std rounded hover:bg-bg-cell transition-colors"
          >
            Annuler
          </button>
          <button
            type="submit"
            disabled={isPending || !file}
            className="flex items-center gap-2 px-4 py-2 text-sm bg-vinci-blue text-white rounded hover:bg-vinci-blue/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isPending ? (
              <>
                <span className="inline-block w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Import en cours...
              </>
            ) : (
              <>
                <Upload size={14} />
                Importer et parser
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Etat vide
// ---------------------------------------------------------------------------

function EmptyState({ onUpload }: { onUpload: () => void }) {
  return (
    <div className="border-2 border-dashed border-border-std rounded p-12 text-center">
      <FileSpreadsheet size={40} className="mx-auto mb-3 text-text-tertiary" />
      <p className="text-sm font-medium text-text-primary mb-1">Aucun export CANECO importe</p>
      <p className="text-xs text-text-tertiary mb-4">
        Importez votre fichier export CANECO BT (.xls ou .xlsx) pour visualiser les departs.
      </p>
      <button
        onClick={onUpload}
        className="inline-flex items-center gap-2 px-4 py-2 text-sm bg-vinci-blue text-white rounded hover:bg-vinci-blue/90 transition-colors"
      >
        <Upload size={14} />
        Importer un fichier CANECO
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Composant utilitaire
// ---------------------------------------------------------------------------

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex gap-4">
      <dt className="w-28 text-text-tertiary shrink-0">{label}</dt>
      <dd className="text-text-primary">{value}</dd>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Onglet Bordereau
// ---------------------------------------------------------------------------

const BDP_PAGE_SIZES = [25, 50, 100, 200] as const;
type BdpPageSize = (typeof BDP_PAGE_SIZES)[number];

const BDP_COLUMNS = [
  { key: "num_prix" as const, label: "N°Prix", width: "min-w-[70px]" },
  { key: "designation" as const, label: "Designation", width: "min-w-[220px]" },
  { key: "sous_famille" as const, label: "Sous-famille", width: "min-w-[180px]" },
  { key: "unite" as const, label: "Unite", width: "min-w-[56px]" },
  { key: "quantite" as const, label: "Quantite", width: "min-w-[80px]", numeric: true },
  { key: "detected_kind" as const, label: "Type", width: "min-w-[90px]" },
  { key: "detected_section_mm2" as const, label: "Section mm2", width: "min-w-[90px]" },
  { key: "detected_material" as const, label: "Materiau", width: "min-w-[80px]" },
  { key: "detected_cable_type" as const, label: "Type cable", width: "min-w-[100px]" },
] as const;

function BordereauTab({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const [selectedImportId, setSelectedImportId] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState<BdpPageSize>(50);
  const [sectionCode, setSectionCode] = useState("");
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [showUpload, setShowUpload] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [editIndiceId, setEditIndiceId] = useState<string | null>(null);

  const { data: imports, isLoading: loadingImports } = useQuery({
    queryKey: ["bordereau", projectId],
    queryFn: () => listBordereau(projectId),
  });

  const { data: detail, isLoading: loadingDetail } = useQuery({
    queryKey: ["bordereau-detail", projectId, selectedImportId, page, perPage, sectionCode, search],
    queryFn: () => getBordereau(projectId, selectedImportId!, page, perPage, sectionCode, search),
    enabled: !!selectedImportId,
  });

  const { mutate: doDeleteImport, isPending: isDeleting } = useMutation({
    mutationFn: (importId: string) => deleteBordereau(projectId, importId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bordereau", projectId] });
      if (confirmDeleteId === selectedImportId) setSelectedImportId(null);
      setConfirmDeleteId(null);
    },
  });

  const { mutate: doUpdateIndice } = useMutation({
    mutationFn: ({ importId, indice }: { importId: string; indice: string }) =>
      updateBordereauIndice(projectId, importId, indice),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bordereau", projectId] });
      setEditIndiceId(null);
    },
  });

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setSearch(searchInput);
    setPage(1);
  }

  function handleClearSearch() {
    setSearchInput("");
    setSearch("");
    setPage(1);
  }

  function handleSelectImport(imp: BordereauImport) {
    setSelectedImportId(imp.id);
    setPage(1);
    setSearch("");
    setSearchInput("");
    setSectionCode("");
    setShowUpload(false);
  }

  if (loadingImports) {
    return <div className="p-6 text-sm text-text-tertiary">Chargement...</div>;
  }

  const hasImports = imports && imports.length > 0;
  const selectedImport = imports?.find((i) => i.id === selectedImportId) ?? null;
  const hasTable = !!selectedImportId && !!selectedImport;

  return (
    <div className="flex-1 min-h-0 flex flex-col">
      {hasTable ? (
        /* Mode tableau ouvert */
        <>
          <div className="shrink-0 px-6 py-2 border-b border-border-std bg-white flex items-center justify-between gap-4">
            <div className="flex items-center gap-2 min-w-0 text-xs">
              <button
                onClick={() => setSelectedImportId(null)}
                className="flex items-center gap-1 text-text-tertiary hover:text-vinci-blue transition-colors shrink-0"
              >
                <ChevronLeft size={13} />
                Imports
              </button>
              <span className="text-text-tertiary shrink-0">/</span>
              {selectedImport.indice && (
                <span className="font-semibold px-2 py-0.5 rounded bg-vinci-blue text-white shrink-0">
                  Indice {selectedImport.indice}
                </span>
              )}
              <span className="text-status-ok shrink-0">
                {selectedImport.total_articles} articles
              </span>
              <span className="text-text-tertiary shrink-0">·</span>
              <span className="text-status-ok shrink-0">
                {selectedImport.sections_count} sections
              </span>
              <span className="text-text-tertiary shrink-0">·</span>
              <span className="truncate text-text-tertiary">{selectedImport.file_name}</span>
              {selectedImport.sheet_name && (
                <>
                  <span className="text-text-tertiary shrink-0">·</span>
                  <span className="truncate text-text-tertiary shrink-0 font-mono text-xs">
                    {selectedImport.sheet_name}
                  </span>
                </>
              )}
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={() => setEditIndiceId(selectedImport.id)}
                className="flex items-center gap-1 px-2 py-1 text-xs border border-border-std rounded hover:bg-bg-cell transition-colors text-text-secondary"
              >
                <Pencil size={11} />
                Indice
              </button>
              <button
                onClick={() => { setShowUpload(true); setSelectedImportId(null); }}
                className="flex items-center gap-1 px-2 py-1 text-xs bg-vinci-blue text-white rounded hover:bg-vinci-blue/90 transition-colors"
              >
                <Upload size={11} />
                Importer
              </button>
            </div>
          </div>

          <div className="flex-1 min-h-0 px-6 pb-4 flex flex-col pt-3">
            <BdpLinesTable
              detail={detail ?? null}
              isLoading={loadingDetail}
              page={page}
              perPage={perPage}
              sectionCode={sectionCode}
              search={search}
              searchInput={searchInput}
              onPageChange={(p) => setPage(p)}
              onPerPageChange={(pp) => { setPerPage(pp); setPage(1); }}
              onSectionChange={(s) => { setSectionCode(s); setPage(1); }}
              onSearchSubmit={handleSearch}
              onSearchInputChange={setSearchInput}
              onClearSearch={handleClearSearch}
            />
          </div>
        </>
      ) : (
        /* Mode liste des imports */
        <div className="flex-1 min-h-0 overflow-auto px-6 pt-4 pb-6 space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-text-primary">
                Bordereau des prix — electricite CFO
                {hasImports && (
                  <span className="ml-2 text-xs font-normal text-text-tertiary">
                    {imports.length} import{imports.length > 1 ? "s" : ""}
                  </span>
                )}
              </h3>
              <p className="text-xs text-text-tertiary mt-0.5">
                Seule la feuille BDP_ELECTRICITE CFO est analysee en V1.
              </p>
            </div>
            <button
              onClick={() => setShowUpload((v) => !v)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-vinci-blue text-white rounded hover:bg-vinci-blue/90 transition-colors"
            >
              <Upload size={13} />
              Importer un bordereau
            </button>
          </div>

          {showUpload && (
            <BdpUploadForm
              projectId={projectId}
              onDone={(newImport) => {
                queryClient.invalidateQueries({ queryKey: ["bordereau", projectId] });
                setShowUpload(false);
                setSelectedImportId(newImport.id);
                setPage(1);
              }}
              onCancel={() => setShowUpload(false)}
            />
          )}

          {!hasImports && !showUpload && (
            <div className="border-2 border-dashed border-border-std rounded p-12 text-center">
              <FileSpreadsheet size={40} className="mx-auto mb-3 text-text-tertiary" />
              <p className="text-sm font-medium text-text-primary mb-1">
                Aucun bordereau importe
              </p>
              <p className="text-xs text-text-tertiary mb-4">
                Importez le fichier bordereau .xlsx (feuille BDP_ELECTRICITE CFO).
              </p>
              <button
                onClick={() => setShowUpload(true)}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm bg-vinci-blue text-white rounded hover:bg-vinci-blue/90 transition-colors"
              >
                <Upload size={14} />
                Importer un bordereau
              </button>
            </div>
          )}

          {hasImports && (
            <div className="grid grid-cols-1 gap-2">
              {imports.map((imp, idx) => (
                <BdpImportCard
                  key={imp.id}
                  imp={imp}
                  isFirst={idx === 0}
                  onSelect={() => handleSelectImport(imp)}
                  onDelete={() => setConfirmDeleteId(imp.id)}
                  onEditIndice={() => setEditIndiceId(imp.id)}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {confirmDeleteId && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded w-full max-w-sm shadow-lg p-6">
            <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center mb-4">
              <Trash2 size={18} className="text-status-warn" />
            </div>
            <h3 className="font-semibold text-text-primary mb-2">Supprimer l'import</h3>
            <p className="text-sm text-text-secondary mb-6">
              Cette action supprimera definitivement cet import bordereau et toutes ses lignes.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setConfirmDeleteId(null)}
                disabled={isDeleting}
                className="px-4 py-2 text-sm text-text-secondary border border-border-std rounded hover:bg-bg-cell transition-colors"
              >
                Annuler
              </button>
              <button
                onClick={() => doDeleteImport(confirmDeleteId)}
                disabled={isDeleting}
                className="px-4 py-2 text-sm bg-red-600 text-white rounded hover:bg-red-700 transition-colors disabled:opacity-50"
              >
                {isDeleting ? "Suppression..." : "Supprimer"}
              </button>
            </div>
          </div>
        </div>
      )}

      {editIndiceId && (
        <IndiceModal
          currentIndice={imports?.find((i) => i.id === editIndiceId)?.indice ?? ""}
          onSave={(indice) => doUpdateIndice({ importId: editIndiceId, indice })}
          onClose={() => setEditIndiceId(null)}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Carte import bordereau
// ---------------------------------------------------------------------------

function BdpImportCard({
  imp,
  isFirst,
  onSelect,
  onDelete,
  onEditIndice,
}: {
  imp: BordereauImport;
  isFirst: boolean;
  onSelect: () => void;
  onDelete: () => void;
  onEditIndice: () => void;
}) {
  const statusConfig = {
    parsed: { label: "Parse", cls: "bg-green-100 text-status-ok" },
    parsing: { label: "En cours...", cls: "bg-yellow-100 text-yellow-700" },
    error: { label: "Erreur", cls: "bg-red-100 text-status-warn" },
    uploaded: { label: "Upload OK", cls: "bg-blue-100 text-vinci-blue" },
  } as const;

  const cfg = statusConfig[imp.status] ?? { label: imp.status, cls: "bg-bg-cell text-text-tertiary" };
  const histBadge = isFirst
    ? { label: "actif", cls: "bg-green-100 text-status-ok" }
    : { label: "ancien", cls: "bg-gray-100 text-text-tertiary" };

  return (
    <div
      className="border border-border-std rounded p-3.5 cursor-pointer bg-white hover:border-vinci-blue/40 transition-colors group"
      onClick={onSelect}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <FileSpreadsheet size={16} className="text-text-tertiary shrink-0" />
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 flex-wrap">
              {imp.indice && (
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-vinci-blue text-white">
                  Indice {imp.indice}
                </span>
              )}
              <span className={cn("text-xs px-2 py-0.5 rounded", histBadge.cls)}>
                {histBadge.label}
              </span>
              <span className={cn("text-xs px-2 py-0.5 rounded", cfg.label === "Erreur" ? cfg.cls : cfg.cls)}>
                {cfg.label}
              </span>
              {imp.total_articles !== null && (
                <span className="text-xs text-text-tertiary">
                  {imp.total_articles} articles
                </span>
              )}
              {imp.sections_count !== null && (
                <span className="text-xs text-text-tertiary">
                  {imp.sections_count} sections
                </span>
              )}
            </div>
            <p className="text-xs text-text-tertiary mt-0.5 truncate">
              {imp.file_name}
              {imp.sheet_name && (
                <span className="ml-1.5 font-mono text-text-tertiary/70">({imp.sheet_name})</span>
              )}
            </p>
            {imp.status === "error" && imp.error_message && (
              <p className="text-xs text-status-warn mt-0.5 truncate">{imp.error_message}</p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <span className="text-xs text-text-tertiary hidden sm:block">
            {formatDateTime(imp.created_at)}
          </span>
          <button
            onClick={(e) => { e.stopPropagation(); onEditIndice(); }}
            className="opacity-0 group-hover:opacity-100 transition-opacity text-text-tertiary hover:text-vinci-blue"
            title="Modifier l'indice"
          >
            <Pencil size={13} />
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onDelete(); }}
            className="opacity-0 group-hover:opacity-100 transition-opacity text-text-tertiary hover:text-status-warn"
            title="Supprimer cet import"
          >
            <Trash2 size={13} />
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tableau paginé bordereau avec en-tetes epingles
// ---------------------------------------------------------------------------

function BdpLinesTable({
  detail,
  isLoading,
  page,
  perPage,
  sectionCode,
  search,
  searchInput,
  onPageChange,
  onPerPageChange,
  onSectionChange,
  onSearchSubmit,
  onSearchInputChange,
  onClearSearch,
}: {
  detail: BordereauDetail | null;
  isLoading: boolean;
  page: number;
  perPage: BdpPageSize;
  sectionCode: string;
  search: string;
  searchInput: string;
  onPageChange: (p: number) => void;
  onPerPageChange: (pp: BdpPageSize) => void;
  onSectionChange: (s: string) => void;
  onSearchSubmit: (e: React.FormEvent) => void;
  onSearchInputChange: (v: string) => void;
  onClearSearch: () => void;
}) {
  const total = detail?.total ?? 0;
  const total_pages = detail?.total_pages ?? 1;
  const rangeStart = total === 0 ? 0 : (page - 1) * perPage + 1;
  const rangeEnd = Math.min(page * perPage, total);

  // Sections disponibles pour le filtre dropdown (uniquement les sous-sections NNN)
  const sections: BordereauSection[] = detail?.sections ?? [];
  const subSections = sections.filter((s) => /^\d{3}$/.test(s.code));

  return (
    <div className="flex-1 min-h-0 flex flex-col gap-2">
      {/* Barre controles */}
      <div className="shrink-0 flex flex-wrap items-center justify-between gap-3 bg-white border border-border-std rounded px-3 py-2">
        <div className="flex items-center gap-2 flex-wrap min-w-0">
          {/* Filtre section */}
          <select
            value={sectionCode}
            onChange={(e) => onSectionChange(e.target.value)}
            className="text-xs border border-border-std rounded px-2 py-1 bg-white focus:outline-none focus:border-vinci-blue"
          >
            <option value="">Toutes sections</option>
            {subSections.map((s) => (
              <option key={s.id} value={s.code}>
                {s.code} — {s.title ?? ""}
              </option>
            ))}
          </select>

          {/* Recherche libre */}
          <form onSubmit={onSearchSubmit} className="flex items-center gap-1.5">
            <div className="relative flex items-center">
              <Search size={13} className="absolute left-2 text-text-tertiary pointer-events-none" />
              <input
                type="text"
                value={searchInput}
                onChange={(e) => onSearchInputChange(e.target.value)}
                placeholder="Recherche libre..."
                className="pl-7 pr-7 py-1 text-xs border border-border-std rounded focus:outline-none focus:border-vinci-blue w-44"
              />
              {searchInput && (
                <button
                  type="button"
                  onClick={onClearSearch}
                  className="absolute right-2 text-text-tertiary hover:text-text-primary"
                >
                  <X size={12} />
                </button>
              )}
            </div>
            <button
              type="submit"
              className="px-2 py-1 text-xs bg-vinci-blue text-white rounded hover:bg-vinci-blue/90 transition-colors"
            >
              Ok
            </button>
          </form>
        </div>

        {/* Compteur + taille page + pagination */}
        <div className="flex items-center gap-3 shrink-0">
          <span className="text-xs text-text-tertiary">
            {total} article{total !== 1 ? "s" : ""} — {rangeStart}–{rangeEnd}
          </span>
          <div className="flex items-center gap-1">
            <label className="text-xs text-text-tertiary">Lignes :</label>
            <select
              value={perPage}
              onChange={(e) => onPerPageChange(Number(e.target.value) as BdpPageSize)}
              className="text-xs border border-border-std rounded px-1 py-0.5 bg-white focus:outline-none focus:border-vinci-blue"
            >
              {BDP_PAGE_SIZES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-0.5">
            <PageBtn icon={<ChevronFirst size={13} />} onClick={() => onPageChange(1)} disabled={page <= 1} title="Premiere page" />
            <PageBtn icon={<ChevronLeft size={13} />} onClick={() => onPageChange(page - 1)} disabled={page <= 1} title="Page precedente" />
            <PageBtn icon={<ChevronRight size={13} />} onClick={() => onPageChange(page + 1)} disabled={page >= total_pages} title="Page suivante" />
            <PageBtn icon={<ChevronLast size={13} />} onClick={() => onPageChange(total_pages)} disabled={page >= total_pages} title="Derniere page" />
          </div>
        </div>
      </div>

      {/* Tableau avec en-tetes epingles */}
      <div className="flex-1 min-h-0 overflow-auto border border-border-std rounded">
        {isLoading ? (
          <div className="p-8 text-center text-sm text-text-tertiary">Chargement...</div>
        ) : !detail || detail.lines.length === 0 ? (
          <div className="p-8 text-center text-sm text-text-tertiary">
            {search || sectionCode ? "Aucun resultat pour ce filtre." : "Aucun article."}
          </div>
        ) : (
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr>
                <th
                  className="px-3 py-2 text-left font-medium text-white text-xs whitespace-nowrap border-r border-white/10"
                  style={{ background: "#001E50", position: "sticky", top: 0, left: 0, zIndex: 30, minWidth: "48px", boxShadow: "2px 2px 0 rgba(0,0,0,0.08)" }}
                >
                  #
                </th>
                {BDP_COLUMNS.map((col) => (
                  <th
                    key={col.key}
                    className={cn("px-3 py-2 text-left font-medium text-white text-xs whitespace-nowrap border-r border-white/10 last:border-r-0", col.width)}
                    style={{ background: "#001E50", position: "sticky", top: 0, zIndex: 20, boxShadow: "0 2px 0 rgba(0,0,0,0.08)" }}
                  >
                    {col.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {detail.lines.map((line, rowIdx) => {
                const rowBg = rowIdx % 2 === 0 ? "bg-white" : "bg-slate-50";
                return (
                  <tr
                    key={line.id}
                    className={cn("border-b border-slate-200 hover:bg-blue-50/40 transition-colors", rowBg)}
                  >
                    <td
                      className={cn("px-3 py-1.5 font-mono text-text-tertiary border-r border-slate-200", rowBg)}
                      style={{ position: "sticky", left: 0, zIndex: 10 }}
                    >
                      {line.excel_row_number ?? rowIdx + 1}
                    </td>
                    {BDP_COLUMNS.map((col) => {
                      const val = line[col.key];
                      if (val === null || val === undefined) {
                        return (
                          <td key={col.key} className="px-3 py-1.5 whitespace-nowrap">
                            <span className="text-slate-300">—</span>
                          </td>
                        );
                      }
                      return (
                        <td
                          key={col.key}
                          className={cn(
                            "px-3 py-1.5 whitespace-nowrap text-text-primary",
                            "numeric" in col && col.numeric && "font-mono"
                          )}
                        >
                          {typeof val === "number" ? formatNum(val) : String(val)}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {detail && total_pages > 1 && (
        <div className="shrink-0 flex justify-center items-center gap-1">
          <PageBtn icon={<ChevronFirst size={13} />} onClick={() => onPageChange(1)} disabled={page <= 1} title="Premiere page" />
          <PageBtn icon={<ChevronLeft size={13} />} onClick={() => onPageChange(page - 1)} disabled={page <= 1} title="Page precedente" />
          <span className="text-xs text-text-tertiary px-2">{page} / {total_pages}</span>
          <PageBtn icon={<ChevronRight size={13} />} onClick={() => onPageChange(page + 1)} disabled={page >= total_pages} title="Page suivante" />
          <PageBtn icon={<ChevronLast size={13} />} onClick={() => onPageChange(total_pages)} disabled={page >= total_pages} title="Derniere page" />
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Formulaire d'upload bordereau
// ---------------------------------------------------------------------------

function BdpUploadForm({
  projectId,
  onDone,
  onCancel,
}: {
  projectId: string;
  onDone: (imp: BordereauImport) => void;
  onCancel: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [indice, setIndice] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [sheetPreview, setSheetPreview] = useState<BordereauSheetPreview | null>(null);
  const [selectedSheet, setSelectedSheet] = useState("");
  const [loadingSheets, setLoadingSheets] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const { mutate: doUpload, isPending } = useMutation({
    mutationFn: () => uploadBordereau(projectId, file!, indice, selectedSheet),
    onSuccess: (imp) => onDone(imp),
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Erreur lors de l'import.";
      setError(msg);
    },
  });

  const handleFile = useCallback(
    async (f: File) => {
      const ext = f.name.split(".").pop()?.toLowerCase();
      if (ext !== "xlsx") {
        setError("Le bordereau doit etre en format .xlsx.");
        return;
      }
      if (f.size > 50 * 1024 * 1024) {
        setError("Fichier trop volumineux (max 50 Mo).");
        return;
      }
      setFile(f);
      setError(null);
      const detected = detectIndiceFromFilename(f.name);
      if (detected) setIndice(detected);

      // Charger les feuilles disponibles
      setLoadingSheets(true);
      setSheetPreview(null);
      try {
        const preview = await previewBordereauSheets(projectId, f);
        setSheetPreview(preview);
        setSelectedSheet(preview.detected ?? preview.sheets[0] ?? "");
      } catch {
        // En cas d'erreur, continuer sans selection de feuille (auto-detection)
        setSheetPreview(null);
        setSelectedSheet("");
      } finally {
        setLoadingSheets(false);
      }
    },
    [projectId]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const f = e.dataTransfer.files[0];
      if (f) handleFile(f);
    },
    [handleFile]
  );

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) { setError("Veuillez selectionner un fichier."); return; }
    setError(null);
    doUpload();
  }

  return (
    <div className="border border-border-std rounded bg-white p-5">
      <h4 className="text-sm font-semibold text-text-primary mb-4">
        Importer un bordereau de prix
      </h4>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Zone de depot fichier */}
        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          className={cn(
            "border-2 border-dashed rounded p-8 text-center cursor-pointer transition-colors",
            isDragging ? "border-vinci-blue bg-blue-50" :
            file ? "border-green-400 bg-green-50" :
            "border-border-std hover:border-vinci-blue/50 hover:bg-bg-light"
          )}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".xlsx"
            className="hidden"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
          />
          <FileSpreadsheet size={32} className={cn("mx-auto mb-2", file ? "text-green-600" : "text-text-tertiary")} />
          {file ? (
            <div>
              <p className="text-sm font-medium text-text-primary">{file.name}</p>
              <p className="text-xs text-text-tertiary mt-1">{(file.size / 1024).toFixed(0)} Ko — cliquez pour changer</p>
            </div>
          ) : (
            <div>
              <p className="text-sm text-text-secondary">Glissez votre fichier bordereau .xlsx ici</p>
              <p className="text-xs text-text-tertiary mt-1">ou cliquez pour parcourir</p>
            </div>
          )}
        </div>

        {/* Choix de la feuille — s'affiche apres chargement des feuilles */}
        {loadingSheets && (
          <div className="flex items-center gap-2 text-xs text-text-tertiary">
            <span className="inline-block w-3 h-3 border-2 border-vinci-blue/30 border-t-vinci-blue rounded-full animate-spin" />
            Lecture des feuilles...
          </div>
        )}

        {sheetPreview && (
          <div className="space-y-2">
            <label className="block text-sm text-text-secondary">
              Feuille a analyser
            </label>
            <div className="flex flex-wrap gap-2">
              {sheetPreview.sheets.map((sheet) => {
                const isRecommended = sheet === sheetPreview.detected;
                const isSelected = sheet === selectedSheet;
                return (
                  <button
                    key={sheet}
                    type="button"
                    onClick={() => setSelectedSheet(sheet)}
                    className={cn(
                      "px-3 py-1.5 text-xs rounded border transition-colors",
                      isSelected
                        ? "bg-vinci-blue text-white border-vinci-blue"
                        : "bg-white text-text-secondary border-border-std hover:border-vinci-blue/50"
                    )}
                  >
                    {sheet}
                    {isRecommended && !isSelected && (
                      <span className="ml-1.5 text-status-ok">(recommandee)</span>
                    )}
                  </button>
                );
              })}
            </div>
            {selectedSheet && selectedSheet !== sheetPreview.detected && (
              <p className="text-xs text-yellow-700 bg-yellow-50 border border-yellow-200 rounded px-3 py-1.5">
                Feuille non electrique selectionnee — le parser tentera de trouver les articles (N°Prix, Designation, Qte).
              </p>
            )}
            {selectedSheet === sheetPreview.detected && (
              <p className="text-xs text-status-ok">
                Feuille recommandee — detection automatique confirmee.
              </p>
            )}
          </div>
        )}

        {/* Indice optionnel */}
        <div className="flex items-center gap-3">
          <label className="text-sm text-text-secondary shrink-0 w-32">Indice (optionnel)</label>
          <input
            type="text"
            value={indice}
            onChange={(e) => setIndice(e.target.value.toUpperCase())}
            maxLength={10}
            placeholder="ex. A, B, C..."
            className="w-24 border border-border-std rounded px-3 py-2 text-sm font-mono uppercase focus:outline-none focus:border-vinci-blue"
          />
        </div>

        {error && (
          <div className="flex items-start gap-2 text-xs text-status-warn bg-red-50 border border-red-200 rounded px-3 py-2">
            <span className="mt-0.5 shrink-0">&#9888;</span>
            <span>{error}</span>
          </div>
        )}

        <div className="flex gap-3 justify-end">
          <button
            type="button"
            onClick={onCancel}
            disabled={isPending}
            className="px-4 py-2 text-sm text-text-secondary border border-border-std rounded hover:bg-bg-cell transition-colors"
          >
            Annuler
          </button>
          <button
            type="submit"
            disabled={isPending || !file || loadingSheets}
            className="flex items-center gap-2 px-4 py-2 text-sm bg-vinci-blue text-white rounded hover:bg-vinci-blue/90 transition-colors disabled:opacity-50"
          >
            {isPending ? (
              <><span className="inline-block w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Parsing...</>
            ) : (
              <><Upload size={14} /> Importer et parser</>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Onglet CPS
// ---------------------------------------------------------------------------

const RULE_TYPE_LABELS: Record<string, string> = {
  // Sections conducteurs (comparaison directe colonne CANECO)
  section_minimale:        "Section minimale conducteurs",
  section_pe:              "Section PE / PEN",
  section_neutre:          "Section neutre",
  // Chute de tension (comparaison CANECO DeltaU)
  chute_tension_max:       "Chute de tension max.",
  // Cables (comparaison CANECO TypeCable)
  type_cable_requis:       "Type de cable requis",
  cable_resistance_feu:    "Cable resistant au feu",
  cable_blinde:            "Cable blinde",
  tension_isolement:       "Tension d'isolement cable",
  // Protection (comparaison CANECO Courbe / Calibre / Pdc)
  ddr_sensibilite:         "DDR - Sensibilite",
  ddr_type:                "DDR - Type",
  disjoncteur_kind:        "Type disjoncteur",
  courbe_disjoncteur:      "Courbe declenchement",
  pouvoir_coupure:         "Pouvoir de coupure (Icu)",
  calibre_protection:      "Calibre protection",
  // Reseau (comparaison CANECO tension / frequence)
  tension_nominale:        "Tension nominale reseau",
  frequence_reseau:        "Frequence reseau",
  courant_court_circuit:   "Courant de court-circuit Icc",
  schema_mise_terre:       "Schema liaison a la terre",
  selectivite:             "Selectivite",
  // Mise a la terre / equipotentialite
  prise_terre:             "Prise de terre (resistance)",
  liaison_equipotentielle: "Liaison equipotentielle",
  // Mode de pose (comparaison CANECO ModePose)
  mode_pose_cable:         "Mode de pose cables",
  canalisation_enterree:   "Canalisations enterrees",
  marquage_cable:          "Marquage / etiquetage cables",
  // Securite / incendie
  securite_incendie:       "Securite incendie / desenfumage",
  // Alimentation secourue
  alimentation_secourue:   "Alimentation secouree (ASI/UPS)",
  autonomie_secours:       "Autonomie alimentation secours",
  // Materiels
  protection_surtension:   "Protection surtension",
  indice_protection:       "Indice de protection IP",
  indice_choc:             "Indice de choc IK",
  resistance_isolement:    "Resistance d'isolement",
  classe_isolation:        "Classe d'isolation",
  marque_imposee:          "Marque preconisee",
  // Environnement
  condition_environnementale: "Conditions environnementales",
};

function ruleTypeLabel(rt: string): string {
  return RULE_TYPE_LABELS[rt] ?? rt;
}

function confidenceBadge(c: number) {
  if (c >= 0.9) return "bg-green-100 text-green-800 border-green-200";
  if (c >= 0.75) return "bg-yellow-100 text-yellow-800 border-yellow-200";
  return "bg-gray-100 text-gray-600 border-gray-200";
}

const RULE_CANECO_MAP: Record<string, string> = {
  section_minimale:        "Section",
  section_neutre:          "Section N",
  section_pe:              "Section PE",
  chute_tension_max:       "DeltaU",
  type_cable_requis:       "TypeCable",
  tension_isolement:       "TypeCable",
  ddr_sensibilite:         "DDR",
  ddr_type:                "DDR",
  courbe_disjoncteur:      "Courbe",
  pouvoir_coupure:         "Pdc",
  calibre_protection:      "Calibre",
  indice_protection:       "IP",
  indice_choc:             "IK",
  tension_nominale:        "Un",
  courant_court_circuit:   "Icc",
  schema_mise_terre:       "Schema",
  selectivite:             "Selectivite",
  mode_pose_cable:         "ModePose",
};

function CpsRuleRow({ rule, onShowExcerpt }: { rule: CpsRule; onShowExcerpt: (r: CpsRule) => void }) {
  const canecoCol = RULE_CANECO_MAP[rule.rule_type];
  return (
    <tr className="hover:bg-bg-cell transition-colors">
      <td className="px-3 py-2 text-xs text-text-secondary whitespace-nowrap">
        <div className="flex flex-col gap-0.5">
          <span>{ruleTypeLabel(rule.rule_type)}</span>
          <div className="flex items-center gap-1 flex-wrap">
            {rule.context_label && (
              <span className="text-text-tertiary text-[10px]">({rule.context_label})</span>
            )}
            {canecoCol && (
              <span className="px-1 py-px text-[9px] font-semibold bg-vinci-blue/10 text-vinci-blue border border-vinci-blue/20 rounded leading-none">
                CANECO:{canecoCol}
              </span>
            )}
          </div>
        </div>
      </td>
      <td className="px-3 py-2 font-mono text-sm font-semibold text-text-primary whitespace-nowrap">
        {rule.value}
        {rule.unit && <span className="ml-1 text-text-secondary text-xs font-normal">{rule.unit}</span>}
      </td>
      <td className="px-3 py-2 text-xs text-text-secondary max-w-xs">
        {rule.description}
      </td>
      <td className="px-3 py-2 text-xs text-center text-text-tertiary">{rule.source_page}</td>
      <td className="px-3 py-2 text-center">
        <span className={cn("text-xs px-2 py-0.5 rounded border", confidenceBadge(rule.confidence))}>
          {Math.round(rule.confidence * 100)}%
        </span>
      </td>
      <td className="px-3 py-2 text-center">
        {rule.source_excerpt ? (
          <button
            onClick={() => onShowExcerpt(rule)}
            className="text-xs text-vinci-blue hover:underline whitespace-nowrap"
          >
            Voir extrait
          </button>
        ) : (
          <span className="text-text-tertiary text-xs">—</span>
        )}
      </td>
    </tr>
  );
}

function CpsTab({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedImport, setSelectedImport] = useState<CpsImport | null>(null);
  const [excerptRule, setExcerptRule] = useState<CpsRule | null>(null);
  const [deleteTargetId, setDeleteTargetId] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const { data: imports = [], isLoading } = useQuery({
    queryKey: ["cps-imports", projectId],
    queryFn: () => listCpsImports(projectId),
  });

  const { data: detail } = useQuery({
    queryKey: ["cps-import-detail", projectId, selectedImport?.id],
    queryFn: () => getCpsImport(projectId, selectedImport!.id),
    enabled: !!selectedImport && selectedImport.status === "parsed",
  });

  const { mutate: doUpload, isPending: isUploading } = useMutation({
    mutationFn: (file: File) => uploadCps(projectId, file),
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: ["cps-imports", projectId] });
      setSelectedImport(created);
      setUploadError(null);
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Erreur lors de l'upload.";
      setUploadError(msg);
    },
  });

  const { mutate: doDelete } = useMutation({
    mutationFn: (importId: string) => deleteCpsImport(projectId, importId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cps-imports", projectId] });
      if (selectedImport?.id === deleteTargetId) setSelectedImport(null);
      setDeleteTargetId(null);
    },
  });

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setUploadError("Seuls les fichiers PDF sont acceptes.");
      return;
    }
    setUploadError(null);
    doUpload(file);
    e.target.value = "";
  }

  const rules = detail?.rules ?? [];

  const grouped = rules.reduce<Record<string, CpsRule[]>>((acc, r) => {
    if (!acc[r.rule_type]) acc[r.rule_type] = [];
    acc[r.rule_type].push(r);
    return acc;
  }, {});

  return (
    <div className="flex-1 min-h-0 overflow-auto p-6 space-y-5">
      <div>
        <div className="text-xs text-text-secondary bg-blue-50 border border-blue-200 rounded px-4 py-2.5">
          Extraction deterministe V1 — les regles marquees "a valider" necessitent une verification
          manuelle par le BE. La version V2 utilisera un LLM pour ameliorer la precision.
        </div>

        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-text-primary">
            CPS — Cahier des Prescriptions Speciales
          </h2>
          <div className="flex items-center gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              className="hidden"
              onChange={handleFileChange}
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              className="flex items-center gap-2 px-4 py-2 text-sm bg-vinci-blue text-white rounded hover:bg-vinci-blue/90 transition-colors disabled:opacity-50"
            >
              {isUploading ? (
                <>
                  <span className="inline-block w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Parsing...
                </>
              ) : (
                <>
                  <Upload size={14} />
                  Importer un CPS
                </>
              )}
            </button>
          </div>
        </div>

        {uploadError && (
          <div className="text-xs text-status-warn bg-red-50 border border-red-200 rounded px-3 py-2">
            {uploadError}
          </div>
        )}

        {isLoading ? (
          <div className="text-sm text-text-tertiary">Chargement...</div>
        ) : imports.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-text-tertiary">
            <FileSpreadsheet size={40} className="mb-3 opacity-30" />
            <p className="text-sm">Aucun CPS importe.</p>
            <p className="text-xs mt-1">
              Importez le PDF du CPS pour extraire les exigences techniques.
            </p>
          </div>
        ) : (
          <div className="flex flex-wrap gap-3">
            {imports.map((imp) => (
              <button
                key={imp.id}
                onClick={() => setSelectedImport(imp)}
                className={cn(
                  "flex flex-col items-start gap-1 px-4 py-3 rounded border text-left transition-colors min-w-[220px]",
                  selectedImport?.id === imp.id
                    ? "border-vinci-blue bg-vinci-blue/5"
                    : "border-border-std bg-white hover:border-vinci-blue/40"
                )}
              >
                <div className="flex items-center justify-between w-full gap-2">
                  <span className="text-sm font-medium text-text-primary truncate max-w-[160px]">
                    {imp.file_name}
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setDeleteTargetId(imp.id);
                    }}
                    className="text-text-tertiary hover:text-status-warn shrink-0"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
                <div className="flex items-center gap-2 text-xs text-text-secondary">
                  <span
                    className={cn(
                      "px-1.5 py-0.5 rounded text-xs font-medium",
                      imp.status === "parsed"
                        ? "bg-green-100 text-green-800"
                        : imp.status === "error"
                          ? "bg-red-100 text-red-700"
                          : "bg-yellow-100 text-yellow-700"
                    )}
                  >
                    {imp.status}
                  </span>
                  {imp.page_count != null && <span>{imp.page_count} pages</span>}
                  {imp.rules_count != null && <span>{imp.rules_count} regles</span>}
                </div>
                <div className="text-xs text-text-tertiary">{formatDateTime(imp.created_at)}</div>
                {imp.status === "error" && imp.error_message && (
                  <div className="text-xs text-status-warn mt-1 max-w-xs">{imp.error_message}</div>
                )}
              </button>
            ))}
          </div>
        )}

        {selectedImport?.status === "parsed" && detail && (
          <h3 className="text-sm font-semibold text-text-primary">
            Regles extraites — {selectedImport.file_name}
            <span className="ml-2 text-text-tertiary font-normal">
              ({rules.length} regles sur {selectedImport.page_count} pages)
            </span>
          </h3>
        )}
      </div>

      {selectedImport?.status === "parsed" && detail && (
        rules.length === 0 ? (
          <div className="text-sm text-text-tertiary bg-yellow-50 border border-yellow-200 rounded px-4 py-3">
            Aucune regle technique extraite. Verifiez que le PDF contient bien des prescriptions
            chiffrables (sections, chutes de tension, types de cables...).
          </div>
        ) : (
          <div className="border border-border-std rounded">
            <table className="w-full text-sm">
              <thead
                className="sticky top-0 z-10"
                style={{ backgroundColor: "#001E50" }}
              >
                <tr className="text-white text-xs">
                  <th className="px-3 py-2.5 text-left font-medium">Type</th>
                  <th className="px-3 py-2.5 text-left font-medium">Valeur</th>
                  <th className="px-3 py-2.5 text-left font-medium">Description</th>
                  <th className="px-3 py-2.5 text-center font-medium">Page</th>
                  <th className="px-3 py-2.5 text-center font-medium">Confiance</th>
                  <th className="px-3 py-2.5 text-center font-medium">Source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-std">
                {Object.entries(grouped).map(([ruleType, typeRules]) => (
                  <>
                    <tr key={`group-${ruleType}`} className="bg-gray-50">
                      <td
                        colSpan={6}
                        className="px-3 py-1.5 text-xs font-semibold text-text-secondary uppercase tracking-wide"
                      >
                        <span>{ruleTypeLabel(ruleType)}</span>
                        <span className="ml-2 font-normal text-text-tertiary">
                          ({typeRules.length})
                        </span>
                        {RULE_CANECO_MAP[ruleType] && (
                          <span className="ml-2 px-1.5 py-px text-[9px] font-semibold bg-vinci-blue/10 text-vinci-blue border border-vinci-blue/20 rounded leading-none align-middle">
                            vs CANECO
                          </span>
                        )}
                      </td>
                    </tr>
                    {typeRules.map((rule, i) => (
                      <CpsRuleRow
                        key={`${ruleType}-${i}`}
                        rule={rule}
                        onShowExcerpt={setExcerptRule}
                      />
                    ))}
                  </>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}

      {excerptRule && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded shadow-lg max-w-lg w-full p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="font-semibold text-sm text-text-primary">
                Extrait source — page {excerptRule.source_page}
              </h4>
              <button
                onClick={() => setExcerptRule(null)}
                className="text-text-tertiary hover:text-text-primary"
              >
                <X size={16} />
              </button>
            </div>
            <div className="text-xs font-medium text-vinci-blue">{excerptRule.description}</div>
            <blockquote className="text-xs text-text-secondary bg-gray-50 border-l-4 border-vinci-blue/30 px-3 py-2 rounded-r leading-relaxed">
              {excerptRule.source_excerpt}
            </blockquote>
            <div className="flex items-center gap-3 text-xs text-text-tertiary">
              <span>Confiance : {Math.round(excerptRule.confidence * 100)}%</span>
              {excerptRule.requires_validation && (
                <span className="text-yellow-700 bg-yellow-50 border border-yellow-200 rounded px-2 py-0.5">
                  A valider manuellement
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {deleteTargetId && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded shadow-lg max-w-sm w-full p-5 space-y-4">
            <h4 className="font-semibold text-sm text-text-primary">Supprimer cet import CPS ?</h4>
            <p className="text-xs text-text-secondary">
              Toutes les regles extraites seront supprimees. Cette action est irreversible.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setDeleteTargetId(null)}
                className="px-4 py-2 text-sm text-text-secondary border border-border-std rounded hover:bg-bg-cell"
              >
                Annuler
              </button>
              <button
                onClick={() => doDelete(deleteTargetId)}
                className="px-4 py-2 text-sm bg-red-600 text-white rounded hover:bg-red-700"
              >
                Supprimer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Onglet Verifications
// ---------------------------------------------------------------------------

const SEVERITY_META: Record<GapSeverity, { label: string; color: string; bg: string; icon: React.ReactNode }> = {
  BLOQUANT: {
    label: "Bloquant",
    color: "text-red-700",
    bg: "bg-red-100",
    icon: <ShieldAlert size={12} />,
  },
  A_CORRIGER: {
    label: "A corriger",
    color: "text-orange-700",
    bg: "bg-orange-100",
    icon: <AlertCircle size={12} />,
  },
  A_SIGNALER: {
    label: "A signaler",
    color: "text-yellow-700",
    bg: "bg-yellow-100",
    icon: <AlertTriangle size={12} />,
  },
  INFO: {
    label: "Info",
    color: "text-blue-700",
    bg: "bg-blue-100",
    icon: <Info size={12} />,
  },
};

const GAP_STATUS_META: Record<GapStatus, { label: string; color: string }> = {
  ouvert: { label: "Ouvert", color: "text-text-primary" },
  acquitte: { label: "Acquitte", color: "text-yellow-700" },
  justifie: { label: "Justifie", color: "text-blue-700" },
  clos: { label: "Clos", color: "text-status-ok" },
};

const GAP_CODE_LABELS: Record<string, string> = {
  "E-001": "Circuit CANECO absent bordereau",
  "E-002": "Article bordereau sans circuit CANECO",
  "E-003": "Section cable differente",
  "E-004": "Protection mal calibree / reglage",
  "E-005": "Type cable != CPS",
  "E-006": "Matiere conducteur differente",
  "E-007": "DDR absent ou insuffisant",
  "E-008": "Non-conformite NF C 15-100",
  "E-009": "Chute de tension depassee",
  "E-010": "Suggestion bonne pratique",
  "E-011": "Icu insuffisant vs Icc",
  "E-012": "Selectivite non assuree",
  "E-013": "Tableau absent bordereau",
  "E-014": "Cable CPS sans circuit CANECO",
  "E-015": "Section neutre insuffisante",
  "E-016": "Conducteur alu < 16 mm²",
  "E-017": "Type DDR inadapte",
  "E-018": "Courbe declenchement inadaptee",
  "E-019": "Donnee CANECO manquante (Icu/IB/calibre = 0)",
  "E-020": "Regle CPS non respectee",
};

function SeverityBadge({ severity }: { severity: GapSeverity }) {
  const m = SEVERITY_META[severity] ?? SEVERITY_META["INFO"];
  return (
    <span className={cn("inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium", m.bg, m.color)}>
      {m.icon}
      {m.label}
    </span>
  );
}

function GapStatusBadge({ status }: { status: GapStatus }) {
  const m = GAP_STATUS_META[status] ?? GAP_STATUS_META["ouvert"];
  return (
    <span className={cn("text-[10px] font-medium", m.color)}>
      {m.label}
    </span>
  );
}

function RunCard({
  run,
  isSelected,
  onSelect,
  onDelete,
}: {
  run: VerificationRun;
  isSelected: boolean;
  onSelect: () => void;
  onDelete: () => void;
}) {
  const statusMeta = run.status === "done"
    ? { label: "Termine", color: "text-status-ok bg-green-50 border-green-200" }
    : run.status === "error"
    ? { label: "Erreur", color: "text-status-warn bg-red-50 border-red-200" }
    : run.status === "running"
    ? { label: "En cours", color: "text-blue-700 bg-blue-50 border-blue-200" }
    : { label: "En attente", color: "text-text-tertiary bg-bg-cell border-border-std" };

  return (
    <div
      onClick={onSelect}
      className={cn(
        "border rounded p-3 cursor-pointer transition-colors",
        isSelected
          ? "border-vinci-blue bg-vinci-blue/5"
          : "border-border-std hover:border-vinci-blue/40 hover:bg-bg-cell"
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={cn("text-[10px] font-medium px-1.5 py-0.5 rounded border", statusMeta.color)}>
              {statusMeta.label}
            </span>
            {run.status === "done" && run.total_gaps !== null && (
              <span className="text-xs text-text-secondary">
                {run.total_gaps} ecart{run.total_gaps !== 1 ? "s" : ""}
              </span>
            )}
          </div>
          <div className="text-[10px] text-text-tertiary mt-1">{formatDateTime(run.created_at)}</div>
          {run.status === "done" && run.total_gaps !== null && run.total_gaps > 0 && (
            <div className="flex items-center gap-2 mt-1.5 flex-wrap">
              {run.critical_count !== null && run.critical_count > 0 && (
                <span className="text-[10px] text-red-700 bg-red-50 px-1.5 py-0.5 rounded">
                  {run.critical_count} bloquant{run.critical_count !== 1 ? "s" : ""}
                </span>
              )}
              {run.high_count !== null && run.high_count > 0 && (
                <span className="text-[10px] text-orange-700 bg-orange-50 px-1.5 py-0.5 rounded">
                  {run.high_count} a corriger
                </span>
              )}
              {run.medium_count !== null && run.medium_count > 0 && (
                <span className="text-[10px] text-yellow-700 bg-yellow-50 px-1.5 py-0.5 rounded">
                  {run.medium_count} a signaler
                </span>
              )}
              {run.info_count !== null && run.info_count > 0 && (
                <span className="text-[10px] text-blue-700 bg-blue-50 px-1.5 py-0.5 rounded">
                  {run.info_count} info
                </span>
              )}
            </div>
          )}
          {run.error_message && (
            <div className="text-[10px] text-status-warn mt-1 truncate">{run.error_message}</div>
          )}
        </div>
        <button
          onClick={(e) => { e.stopPropagation(); onDelete(); }}
          className="text-text-tertiary hover:text-status-warn transition-colors shrink-0 mt-0.5"
          title="Supprimer ce run"
        >
          <Trash2 size={12} />
        </button>
      </div>
    </div>
  );
}

function GapDetailPanel({
  gap,
  onClose,
  onUpdateStatus,
}: {
  gap: Gap;
  onClose: () => void;
  onUpdateStatus: (gapId: string, status: GapStatus, comment?: string) => void;
}) {
  const [newStatus, setNewStatus] = useState<GapStatus>(gap.status);
  const [comment, setComment] = useState(gap.comment ?? "");

  return (
    <div className="fixed inset-0 bg-black/40 flex items-end sm:items-center justify-center z-50 p-4">
      <div className="bg-white rounded-t sm:rounded shadow-lg w-full max-w-lg max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-border-std shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            <SeverityBadge severity={gap.severity} />
            <span className="font-mono text-xs text-text-tertiary">{gap.code}</span>
            <span className="text-sm font-medium text-text-primary truncate">{gap.title}</span>
          </div>
          <button onClick={onClose} className="text-text-tertiary hover:text-text-primary shrink-0">
            <X size={16} />
          </button>
        </div>

        {/* Body */}
        <div className="overflow-auto flex-1 p-5 space-y-4">
          <div>
            <div className="text-xs font-medium text-text-tertiary uppercase tracking-wide mb-1">Description</div>
            <p className="text-sm text-text-primary leading-relaxed">{gap.description}</p>
          </div>

          {gap.suggested_action && (
            <div>
              <div className="text-xs font-medium text-text-tertiary uppercase tracking-wide mb-1">Action suggeree</div>
              <p className="text-sm text-blue-700 bg-blue-50 rounded p-2 leading-relaxed">{gap.suggested_action}</p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3 text-xs">
            {gap.caneco_repere && (
              <div>
                <div className="text-text-tertiary mb-0.5">Repere CANECO</div>
                <div className="font-mono font-medium">{gap.caneco_repere}</div>
              </div>
            )}
            {gap.caneco_amont && (
              <div>
                <div className="text-text-tertiary mb-0.5">Amont (tableau)</div>
                <div className="font-mono font-medium">{gap.caneco_amont}</div>
              </div>
            )}
            {gap.caneco_row != null && (
              <div>
                <div className="text-text-tertiary mb-0.5">Ligne CANECO (Excel)</div>
                <div className="font-mono font-medium">L. {gap.caneco_row}</div>
              </div>
            )}
            {gap.bordereau_num_prix && (
              <div>
                <div className="text-text-tertiary mb-0.5">N° Prix bordereau</div>
                <div className="font-mono font-medium">{gap.bordereau_num_prix}</div>
              </div>
            )}
            {gap.bordereau_row != null && (
              <div>
                <div className="text-text-tertiary mb-0.5">Ligne bordereau (Excel)</div>
                <div className="font-mono font-medium">L. {gap.bordereau_row}</div>
              </div>
            )}
            {gap.norm_rule_code && (
              <div>
                <div className="text-text-tertiary mb-0.5">Regle normative</div>
                <div className="font-medium">{gap.norm_rule_code}</div>
              </div>
            )}
          </div>

          {gap.fields_compared && Object.keys(gap.fields_compared).length > 0 && (
            <div>
              <div className="text-xs font-medium text-text-tertiary uppercase tracking-wide mb-1">Champs compares</div>
              <div className="bg-bg-cell rounded p-2 space-y-1">
                {Object.entries(gap.fields_compared).map(([k, v]) => {
                  // Affichage monospace pour les valeurs brutes CANECO/bordereau
                  // (5G6, 4X(1x300), 1x150, etc.) plus lisible que la simple coercition
                  const isRaw =
                    k.includes("brut") || k.includes("cable") || k.includes("section_bordereau");
                  const display =
                    v === null || v === undefined
                      ? "—"
                      : Array.isArray(v)
                      ? v.join(", ")
                      : String(v);
                  return (
                    <div key={k} className="flex items-center justify-between gap-3 text-xs">
                      <span className="text-text-secondary font-mono">{k}</span>
                      <span
                        className={cn(
                          "font-medium text-text-primary text-right break-all",
                          isRaw && "font-mono bg-white px-1.5 py-0.5 rounded border border-border-std"
                        )}
                      >
                        {display}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Statut */}
          <div className="pt-2 border-t border-border-std space-y-2">
            <div className="text-xs font-medium text-text-tertiary uppercase tracking-wide">Gestion de l'ecart</div>
            <div className="flex items-center gap-2">
              <select
                value={newStatus}
                onChange={(e) => setNewStatus(e.target.value as GapStatus)}
                className="text-sm border border-border-std rounded px-2 py-1 focus:outline-none focus:border-vinci-blue bg-white"
              >
                <option value="ouvert">Ouvert</option>
                <option value="acquitte">Acquitte</option>
                <option value="justifie">Justifie</option>
                <option value="clos">Clos</option>
              </select>
            </div>
            <textarea
              rows={2}
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Commentaire (optionnel)..."
              className="w-full text-sm border border-border-std rounded px-2 py-1.5 focus:outline-none focus:border-vinci-blue resize-none"
            />
            <button
              onClick={() => onUpdateStatus(gap.id, newStatus, comment || undefined)}
              disabled={newStatus === gap.status && !comment}
              className="px-4 py-1.5 text-sm bg-vinci-blue text-white rounded hover:bg-vinci-blue/90 transition-colors disabled:opacity-40"
            >
              Enregistrer
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function VerificationsTab({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [filterSeverity, setFilterSeverity] = useState<string>("");
  const [filterStatus, setFilterStatus] = useState<string>("");
  // Vue ingenieur : masque INFO + A_SIGNALER, focus sur les ecarts actionnables
  const [engineerView, setEngineerView] = useState<boolean>(true);
  const [confirmDeleteRunId, setConfirmDeleteRunId] = useState<string | null>(null);
  const [selectedGap, setSelectedGap] = useState<Gap | null>(null);

  // Lancer un run
  const [showLaunch, setShowLaunch] = useState(false);
  const [launchCaneco, setLaunchCaneco] = useState("");
  const [launchBordereau, setLaunchBordereau] = useState("");
  const [launchCps, setLaunchCps] = useState("");
  const [launchIcc, setLaunchIcc] = useState("");
  const [launchError, setLaunchError] = useState<string | null>(null);

  // Donnees
  const { data: runs, isLoading: loadingRuns } = useQuery({
    queryKey: ["verification-runs", projectId],
    queryFn: () => listVerificationRuns(projectId),
  });

  const { data: runDetail, isLoading: loadingDetail } = useQuery({
    queryKey: ["verification-run-detail", projectId, selectedRunId],
    queryFn: () => getVerificationRun(projectId, selectedRunId!),
    enabled: !!selectedRunId,
  });

  // Donnees pour le formulaire de lancement
  const { data: exportsForForm } = useQuery({
    queryKey: ["caneco", projectId],
    queryFn: () => listCaneco(projectId),
  });
  const { data: bordereauForForm } = useQuery({
    queryKey: ["bordereau", projectId],
    queryFn: () => listBordereau(projectId),
  });
  const { data: cpsForForm } = useQuery({
    queryKey: ["cps", projectId],
    queryFn: () => listCpsImports(projectId),
  });

  const { mutate: doCreate, isPending: isCreating } = useMutation({
    mutationFn: () =>
      createVerificationRun(projectId, {
        caneco_export_id: launchCaneco,
        bordereau_import_id: launchBordereau,
        cps_import_id: launchCps || undefined,
        icc_presumed_ka: launchIcc ? parseFloat(launchIcc) : undefined,
      }),
    onSuccess: (run) => {
      queryClient.invalidateQueries({ queryKey: ["verification-runs", projectId] });
      setSelectedRunId(run.id);
      setShowLaunch(false);
      setLaunchError(null);
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Erreur lors du lancement.";
      setLaunchError(msg);
    },
  });

  const { mutate: doDeleteRun } = useMutation({
    mutationFn: (runId: string) => deleteVerificationRun(projectId, runId),
    onSuccess: (_, runId) => {
      queryClient.invalidateQueries({ queryKey: ["verification-runs", projectId] });
      if (selectedRunId === runId) setSelectedRunId(null);
      setConfirmDeleteRunId(null);
    },
  });

  const { mutate: doUpdateGap } = useMutation({
    mutationFn: ({ gapId, status, comment }: { gapId: string; status: GapStatus; comment?: string }) =>
      updateGapStatus(projectId, selectedRunId!, gapId, { status, comment }),
    onSuccess: (updatedGap) => {
      queryClient.setQueryData(
        ["verification-run-detail", projectId, selectedRunId],
        (old: VerificationRunDetail | undefined) => {
          if (!old) return old;
          return {
            ...old,
            gaps: old.gaps.map((g) => (g.id === updatedGap.id ? updatedGap : g)),
          };
        }
      );
      setSelectedGap(null);
    },
  });

  // Filtre local sur les gaps
  const filteredGaps = (runDetail?.gaps ?? []).filter((g) => {
    if (engineerView && (g.severity === "INFO" || g.severity === "A_SIGNALER")) return false;
    if (filterSeverity && g.severity !== filterSeverity) return false;
    if (filterStatus && g.status !== filterStatus) return false;
    return true;
  });

  // KPI du run selectionne
  const kpis = runDetail
    ? [
        { label: "Bloquants", severity: "BLOQUANT" as const, count: runDetail.critical_count ?? 0, color: "text-red-700", bg: "bg-red-50 border-red-200", ring: "ring-red-400" },
        { label: "A corriger", severity: "A_CORRIGER" as const, count: runDetail.high_count ?? 0, color: "text-orange-700", bg: "bg-orange-50 border-orange-200", ring: "ring-orange-400" },
        { label: "A signaler", severity: "A_SIGNALER" as const, count: runDetail.medium_count ?? 0, color: "text-yellow-700", bg: "bg-yellow-50 border-yellow-200", ring: "ring-yellow-400" },
        { label: "Info", severity: "INFO" as const, count: runDetail.info_count ?? 0, color: "text-blue-700", bg: "bg-blue-50 border-blue-200", ring: "ring-blue-400" },
      ]
    : [];

  // Toggle filter via clic sur une KPI : applique la severite ou retire le filtre si deja actif.
  // Desactive la "Vue ingenieur" pour respecter le choix utilisateur (sinon Info/A signaler restent masques).
  function toggleKpiFilter(severity: "BLOQUANT" | "A_CORRIGER" | "A_SIGNALER" | "INFO") {
    if (filterSeverity === severity) {
      setFilterSeverity("");
    } else {
      setFilterSeverity(severity);
      if (severity === "A_SIGNALER" || severity === "INFO") {
        setEngineerView(false);
      }
    }
  }

  if (loadingRuns) {
    return <div className="p-6 text-sm text-text-tertiary">Chargement...</div>;
  }

  return (
    <div className="flex-1 min-h-0 overflow-auto p-6 space-y-5">

      {/* Bandeau intro */}
      <div className="bg-vinci-blue/5 border border-vinci-blue/20 rounded p-3 text-xs text-vinci-blue">
        Le moteur de verification croise l'export CANECO, le bordereau et les regles CPS
        pour detecter les ecarts et non-conformites NF C 15-100.
      </div>

      {/* Header + bouton lancer */}
      <div className="flex items-center justify-between gap-4">
        <h3 className="text-sm font-semibold text-text-primary">Historique des verifications</h3>
        <button
          onClick={() => setShowLaunch(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-vinci-blue text-white rounded hover:bg-vinci-blue/90 transition-colors"
        >
          <Play size={11} />
          Lancer une verification
        </button>
      </div>

      {/* Liste des runs */}
      {(!runs || runs.length === 0) ? (
        <div className="border border-dashed border-border-std rounded p-8 text-center">
          <ShieldAlert size={28} className="mx-auto text-text-tertiary mb-2" />
          <p className="text-sm text-text-secondary">Aucune verification lancee.</p>
          <p className="text-xs text-text-tertiary mt-1">
            Cliquez sur "Lancer une verification" pour analyser les donnees du projet.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {runs.map((r) => (
            <RunCard
              key={r.id}
              run={r}
              isSelected={r.id === selectedRunId}
              onSelect={() => setSelectedRunId(r.id)}
              onDelete={() => setConfirmDeleteRunId(r.id)}
            />
          ))}
        </div>
      )}

      {/* Detail du run selectionne */}
      {selectedRunId && runDetail && (
        <div className="space-y-4">
          {/* KPI cards — cliquables pour filtrer */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {kpis.map((kpi) => {
              const active = filterSeverity === kpi.severity;
              return (
                <button
                  key={kpi.label}
                  type="button"
                  onClick={() => toggleKpiFilter(kpi.severity)}
                  title={
                    active
                      ? `Cliquer pour retirer le filtre "${kpi.label}"`
                      : `Cliquer pour filtrer sur "${kpi.label}"`
                  }
                  className={cn(
                    "border rounded p-3 text-center transition-all cursor-pointer select-none",
                    "hover:shadow-md hover:-translate-y-0.5",
                    "focus:outline-none focus-visible:ring-2 focus-visible:ring-vinci-blue",
                    kpi.bg,
                    active && cn("ring-2 ring-offset-1", kpi.ring)
                  )}
                >
                  <div className={cn("text-2xl font-bold", kpi.color)}>{kpi.count}</div>
                  <div className={cn("text-[11px] font-medium mt-0.5", kpi.color)}>
                    {kpi.label}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Barre de filtres */}
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-xs text-text-tertiary">Filtrer :</span>
            <label className="flex items-center gap-1.5 text-xs text-text-secondary cursor-pointer select-none">
              <input
                type="checkbox"
                checked={engineerView}
                onChange={(e) => setEngineerView(e.target.checked)}
                className="accent-vinci-blue"
              />
              Vue ingénieur (Bloquants + A corriger)
            </label>
            <select
              value={filterSeverity}
              onChange={(e) => setFilterSeverity(e.target.value)}
              disabled={engineerView}
              className="text-xs border border-border-std rounded px-2 py-1 bg-white focus:outline-none focus:border-vinci-blue disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <option value="">Toutes severites</option>
              <option value="BLOQUANT">Bloquant</option>
              <option value="A_CORRIGER">A corriger</option>
              <option value="A_SIGNALER">A signaler</option>
              <option value="INFO">Info</option>
            </select>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="text-xs border border-border-std rounded px-2 py-1 bg-white focus:outline-none focus:border-vinci-blue"
            >
              <option value="">Tous statuts</option>
              <option value="ouvert">Ouvert</option>
              <option value="acquitte">Acquitte</option>
              <option value="justifie">Justifie</option>
              <option value="clos">Clos</option>
            </select>
            <span className="text-xs text-text-tertiary ml-auto">
              {filteredGaps.length} ecart{filteredGaps.length !== 1 ? "s" : ""}
              {runDetail.duration_seconds !== null && (
                <span> — {runDetail.duration_seconds.toFixed(1)}s</span>
              )}
            </span>
          </div>

          {/* Tableau des ecarts */}
          {filteredGaps.length === 0 ? (
            <div className="border border-border-std rounded p-6 text-center">
              <CheckCircle2 size={24} className="mx-auto text-status-ok mb-2" />
              <p className="text-sm text-text-secondary">
                {runDetail.total_gaps === 0
                  ? "Aucun ecart detecte sur ce run."
                  : "Aucun ecart ne correspond aux filtres actifs."}
              </p>
            </div>
          ) : (
            <div className="border border-border-std rounded">
              <table className="w-full text-xs">
                <thead className="sticky top-0 z-10" style={{ backgroundColor: "#001E50" }}>
                  <tr>
                    <th className="px-3 py-2 text-left font-medium text-white/80 w-[90px]">Code</th>
                    <th className="px-3 py-2 text-left font-medium text-white/80 w-[100px]">Severite</th>
                    <th className="px-3 py-2 text-left font-medium text-white/80">Titre</th>
                    <th className="px-3 py-2 text-left font-medium text-white/80 w-[140px] hidden sm:table-cell">Repere</th>
                    <th className="px-3 py-2 text-left font-medium text-white/80 w-[120px] hidden md:table-cell">Amont</th>
                    <th className="px-3 py-2 text-left font-medium text-white/80 w-[80px]">Statut</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredGaps.map((gap, i) => (
                    <tr
                      key={gap.id}
                      onClick={() => setSelectedGap(gap)}
                      className={cn(
                        "border-t border-border-std cursor-pointer transition-colors",
                        i % 2 === 0 ? "bg-white" : "bg-bg-cell/40",
                        "hover:bg-vinci-blue/5"
                      )}
                    >
                      <td className="px-3 py-2 font-mono text-text-tertiary" title={GAP_CODE_LABELS[gap.code]}>{gap.code}</td>
                      <td className="px-3 py-2">
                        <SeverityBadge severity={gap.severity} />
                      </td>
                      <td className="px-3 py-2 text-text-primary">
                        <div className="truncate max-w-[300px]">{gap.title}</div>
                        {gap.norm_rule_code && (
                          <div className="text-[10px] text-text-tertiary font-mono">{gap.norm_rule_code}</div>
                        )}
                      </td>
                      <td className="px-3 py-2 font-mono text-text-secondary hidden sm:table-cell">
                        <div>{gap.caneco_repere ?? gap.bordereau_num_prix ?? "—"}</div>
                        {(gap.caneco_row ?? gap.bordereau_row) && (
                          <div className="text-[10px] text-text-tertiary mt-0.5">
                            {gap.caneco_row ? `L. ${gap.caneco_row}` : `L. ${gap.bordereau_row}`}
                          </div>
                        )}
                      </td>
                      <td className="px-3 py-2 font-mono text-text-tertiary hidden md:table-cell">
                        {gap.caneco_amont ?? "—"}
                      </td>
                      <td className="px-3 py-2">
                        <GapStatusBadge status={gap.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {selectedRunId && loadingDetail && (
        <div className="text-sm text-text-tertiary">Chargement des ecarts...</div>
      )}

      {/* Modal lancer verification */}
      {showLaunch && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded shadow-lg w-full max-w-md">
            <div className="flex items-center justify-between px-5 py-4 border-b border-border-std">
              <h3 className="font-semibold text-text-primary">Lancer une verification</h3>
              <button
                onClick={() => { setShowLaunch(false); setLaunchError(null); }}
                className="text-text-tertiary hover:text-text-primary"
              >
                <X size={16} />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <div>
                <label className="block text-xs text-text-secondary mb-1">
                  Export CANECO <span className="text-status-warn">*</span>
                </label>
                <select
                  value={launchCaneco}
                  onChange={(e) => setLaunchCaneco(e.target.value)}
                  className="w-full border border-border-std rounded px-2 py-1.5 text-sm focus:outline-none focus:border-vinci-blue bg-white"
                >
                  <option value="">-- Selectionner --</option>
                  {(exportsForForm ?? [])
                    .filter((e) => e.status === "parsed")
                    .map((e) => (
                      <option key={e.id} value={e.id}>
                        Indice {e.indice} — {e.file_name} ({e.line_count} lignes)
                      </option>
                    ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-text-secondary mb-1">
                  Bordereau <span className="text-status-warn">*</span>
                </label>
                <select
                  value={launchBordereau}
                  onChange={(e) => setLaunchBordereau(e.target.value)}
                  className="w-full border border-border-std rounded px-2 py-1.5 text-sm focus:outline-none focus:border-vinci-blue bg-white"
                >
                  <option value="">-- Selectionner --</option>
                  {(bordereauForForm ?? [])
                    .filter((b) => b.status === "parsed")
                    .map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.file_name} ({b.total_articles} articles)
                      </option>
                    ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-text-secondary mb-1">CPS (optionnel)</label>
                <select
                  value={launchCps}
                  onChange={(e) => setLaunchCps(e.target.value)}
                  className="w-full border border-border-std rounded px-2 py-1.5 text-sm focus:outline-none focus:border-vinci-blue bg-white"
                >
                  <option value="">-- Sans CPS --</option>
                  {(cpsForForm ?? [])
                    .filter((c) => c.status === "parsed")
                    .map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.file_name} ({c.rules_count} regles)
                      </option>
                    ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-text-secondary mb-1">
                  Icc presume (kA) — defaut 6 kA
                </label>
                <input
                  type="number"
                  min="0.1"
                  max="100"
                  step="0.1"
                  value={launchIcc}
                  onChange={(e) => setLaunchIcc(e.target.value)}
                  placeholder="6"
                  className="w-full border border-border-std rounded px-2 py-1.5 text-sm focus:outline-none focus:border-vinci-blue"
                />
              </div>
              {launchError && <p className="text-xs text-status-warn">{launchError}</p>}
              <div className="flex gap-3 justify-end pt-2">
                <button
                  onClick={() => { setShowLaunch(false); setLaunchError(null); }}
                  className="px-4 py-2 text-sm text-text-secondary border border-border-std rounded hover:bg-bg-cell"
                >
                  Annuler
                </button>
                <button
                  onClick={() => {
                    if (!launchCaneco || !launchBordereau) {
                      setLaunchError("Selectionnez un export CANECO et un bordereau.");
                      return;
                    }
                    doCreate();
                  }}
                  disabled={isCreating}
                  className="px-4 py-2 text-sm bg-vinci-blue text-white rounded hover:bg-vinci-blue/90 disabled:opacity-50"
                >
                  {isCreating ? "Analyse en cours..." : "Lancer la verification"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal detail ecart */}
      {selectedGap && (
        <GapDetailPanel
          gap={selectedGap}
          onClose={() => setSelectedGap(null)}
          onUpdateStatus={(gapId, status, comment) =>
            doUpdateGap({ gapId, status, comment })
          }
        />
      )}

      {/* Confirmation suppression run */}
      {confirmDeleteRunId && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded shadow-lg max-w-sm w-full p-5 space-y-4">
            <h4 className="font-semibold text-sm text-text-primary">Supprimer ce run ?</h4>
            <p className="text-xs text-text-secondary">
              Tous les ecarts associes seront supprimes. Cette action est irreversible.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setConfirmDeleteRunId(null)}
                className="px-4 py-2 text-sm text-text-secondary border border-border-std rounded hover:bg-bg-cell"
              >
                Annuler
              </button>
              <button
                onClick={() => doDeleteRun(confirmDeleteRunId)}
                className="px-4 py-2 text-sm bg-red-600 text-white rounded hover:bg-red-700"
              >
                Supprimer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tableaux electriques + QR — onglet (Module A)
// ---------------------------------------------------------------------------

function TableauxTab({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const [selectedExportId, setSelectedExportId] = useState<string>("");
  const [qrTableau, setQrTableau] = useState<Tableau | null>(null);
  const [isLabels, setIsLabels] = useState(false);
  const [genResult, setGenResult] = useState<string | null>(null);

  const { data: exports } = useQuery({
    queryKey: ["caneco", projectId],
    queryFn: () => listCaneco(projectId),
  });

  const { data: tableaux, isLoading } = useQuery({
    queryKey: ["tableaux", projectId],
    queryFn: () => listTableaux(projectId),
  });

  const effectiveExportId = selectedExportId || exports?.[0]?.id || "";

  const generateMut = useMutation({
    mutationFn: () => generateTableaux(projectId, effectiveExportId),
    onSuccess: (res) => {
      setGenResult(
        `${res.nb_tableaux} tableau(x) et ${res.nb_departs_total} depart(s) ` +
          `generes depuis l'indice ${res.caneco_indice}.`
      );
      queryClient.invalidateQueries({ queryKey: ["tableaux", projectId] });
    },
  });

  async function handleLabels() {
    setIsLabels(true);
    try {
      await downloadLabelsPdf(projectId);
    } finally {
      setIsLabels(false);
    }
  }

  if (!exports || exports.length === 0) {
    return (
      <div className="flex-1 min-h-0 overflow-auto p-6">
        <div className="border border-dashed border-border-std rounded p-8 text-center">
          <QrCode size={28} className="mx-auto text-text-tertiary mb-2" />
          <p className="text-sm text-text-secondary">
            Aucun export CANECO disponible. Importez d'abord un export pour
            generer les tableaux et leurs QR codes.
          </p>
        </div>
      </div>
    );
  }

  const list = tableaux ?? [];
  const totalDeparts = list.reduce((s, t) => s + t.nb_departs, 0);
  const totalLongueur = list.reduce((s, t) => s + t.longueur_totale_m, 0);

  return (
    <div className="flex-1 min-h-0 overflow-auto p-6 space-y-5">
      <div className="bg-vinci-blue/5 border border-vinci-blue/20 rounded p-3 text-xs text-vinci-blue">
        Chaque tableau electrique recoit un QR code unique pointant vers une
        fiche cables consultable sans connexion (lecture seule). La regeneration
        conserve les QR deja imprimes : les etiquettes posees sur les armoires
        restent valides.
      </div>

      <div className="flex items-end gap-3 flex-wrap">
        <div>
          <label className="block text-xs text-text-tertiary mb-1">
            Export CANECO source
          </label>
          <select
            value={effectiveExportId}
            onChange={(e) => setSelectedExportId(e.target.value)}
            className="text-xs border border-border-std rounded px-2 py-1.5 bg-white min-w-[220px]"
          >
            {exports.map((ex) => (
              <option key={ex.id} value={ex.id}>
                Indice {ex.indice} — {ex.file_name}
              </option>
            ))}
          </select>
        </div>
        <button
          type="button"
          onClick={() => generateMut.mutate()}
          disabled={generateMut.isPending || !effectiveExportId}
          className={cn(
            "flex items-center gap-1.5 px-3 py-1.5 text-xs rounded transition-colors",
            "bg-vinci-blue text-white hover:bg-vinci-blue/90",
            "disabled:opacity-50 disabled:cursor-not-allowed"
          )}
        >
          {generateMut.isPending ? (
            <Loader2 size={12} className="animate-spin" />
          ) : (
            <RefreshCw size={12} />
          )}
          {list.length > 0 ? "Mettre a jour les tableaux" : "Generer les tableaux"}
        </button>
        <button
          type="button"
          onClick={handleLabels}
          disabled={isLabels || list.length === 0}
          className={cn(
            "flex items-center gap-1.5 px-3 py-1.5 text-xs rounded transition-colors",
            "border border-vinci-blue text-vinci-blue hover:bg-vinci-blue/5",
            "disabled:opacity-50 disabled:cursor-not-allowed"
          )}
        >
          {isLabels ? (
            <Loader2 size={12} className="animate-spin" />
          ) : (
            <Printer size={12} />
          )}
          Imprimer les etiquettes (PDF A4)
        </button>
      </div>

      {genResult && (
        <div className="text-xs text-green-700 bg-green-50 border border-green-200 rounded px-3 py-2">
          {genResult}
        </div>
      )}
      {generateMut.isError && (
        <div className="text-xs text-status-warn bg-red-50 border border-red-200 rounded px-3 py-2">
          Echec de la generation des tableaux.
        </div>
      )}

      {list.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <KpiCard
            label="Tableaux"
            value={list.length}
            color="text-vinci-blue"
            bg="bg-vinci-blue/5 border-vinci-blue/20"
          />
          <KpiCard
            label="Circuits alimentes (total)"
            value={totalDeparts}
            color="text-text-primary"
            bg="bg-bg-cell border-border-std"
          />
          <KpiCard
            label="Longueur cumulee"
            value={`${formatMeters(totalLongueur)} m`}
            color="text-text-primary"
            bg="bg-bg-cell border-border-std"
          />
        </div>
      )}

      {isLoading && (
        <div className="text-sm text-text-tertiary">Chargement des tableaux...</div>
      )}

      {!isLoading && list.length === 0 && (
        <div className="border border-dashed border-border-std rounded p-8 text-center">
          <QrCode size={26} className="mx-auto text-text-tertiary mb-2" />
          <p className="text-sm text-text-secondary">
            Aucun tableau genere. Cliquez sur « Generer les tableaux » a partir
            de l'export CANECO selectionne.
          </p>
        </div>
      )}

      {list.length > 0 && (
        <div className="border border-border-std rounded overflow-hidden">
          <div className="px-4 py-2 bg-bg-cell border-b border-border-std">
            <h4 className="text-xs font-semibold text-text-tertiary uppercase tracking-wide">
              Tableaux du projet ({list.length})
            </h4>
          </div>
          <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
            <table className="w-full text-xs">
              <thead
                className="sticky top-0 z-10"
                style={{ backgroundColor: "#001E50" }}
              >
                <tr>
                  <th className="px-3 py-2 text-left font-medium text-white/90">
                    Repere
                  </th>
                  <th className="px-3 py-2 text-left font-medium text-white/90">
                    Designation
                  </th>
                  <th className="px-3 py-2 text-right font-medium text-white/90 w-[110px]">
                    Circuits
                  </th>
                  <th className="px-3 py-2 text-right font-medium text-white/90 w-[130px]">
                    Longueur (m)
                  </th>
                  <th className="px-3 py-2 text-right font-medium text-white/90 w-[230px]">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {list.map((t, i) => (
                  <tr
                    key={t.id}
                    className={i % 2 === 0 ? "bg-white" : "bg-bg-cell"}
                  >
                    <td className="px-3 py-2 font-semibold text-vinci-blue border-t border-border-std">
                      {t.repere}
                    </td>
                    <td className="px-3 py-2 text-text-secondary border-t border-border-std">
                      {t.designation || "—"}
                    </td>
                    <td className="px-3 py-2 text-right text-text-primary border-t border-border-std">
                      {t.nb_departs}
                    </td>
                    <td className="px-3 py-2 text-right text-text-primary border-t border-border-std">
                      {formatMeters(t.longueur_totale_m)}
                    </td>
                    <td className="px-3 py-2 border-t border-border-std">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          type="button"
                          onClick={() => setQrTableau(t)}
                          className="flex items-center gap-1 px-2 py-1 rounded border border-border-std hover:bg-bg-light text-text-secondary"
                          title="Afficher le QR code"
                        >
                          <QrCode size={12} /> QR
                        </button>
                        <a
                          href={publicFicheUrl(t.qr_token)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 px-2 py-1 rounded border border-border-std hover:bg-bg-light text-text-secondary"
                          title="Ouvrir la fiche publique"
                        >
                          <ExternalLink size={12} /> Fiche
                        </a>
                        <button
                          type="button"
                          onClick={() => downloadFichePdf(projectId, t.id)}
                          className="flex items-center gap-1 px-2 py-1 rounded border border-border-std hover:bg-bg-light text-text-secondary"
                          title="Telecharger la fiche en PDF"
                        >
                          <FileText size={12} /> PDF
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {qrTableau && (
        <QrModal
          projectId={projectId}
          tableau={qrTableau}
          onClose={() => setQrTableau(null)}
        />
      )}
    </div>
  );
}

function QrModal({
  projectId,
  tableau,
  onClose,
}: {
  projectId: string;
  tableau: Tableau;
  onClose: () => void;
}) {
  const [qrUrl, setQrUrl] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const ficheUrl = publicFicheUrl(tableau.qr_token);

  useEffect(() => {
    let revoke: string | null = null;
    let active = true;
    fetchTableauQrObjectUrl(projectId, tableau.id).then((url) => {
      if (active) {
        revoke = url;
        setQrUrl(url);
      } else {
        URL.revokeObjectURL(url);
      }
    });
    return () => {
      active = false;
      if (revoke) URL.revokeObjectURL(revoke);
    };
  }, [projectId, tableau.id]);

  async function copyLink() {
    await navigator.clipboard.writeText(ficheUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg max-w-sm w-full p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between mb-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-text-tertiary">
              QR — Tableau
            </p>
            <h3 className="text-lg font-bold text-vinci-blue">
              {tableau.repere}
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-text-tertiary hover:text-text-secondary"
          >
            <X size={18} />
          </button>
        </div>

        <div className="flex justify-center mb-4">
          {qrUrl ? (
            <img
              src={qrUrl}
              alt={`QR ${tableau.repere}`}
              className="w-56 h-56 border border-border-std rounded"
            />
          ) : (
            <div className="w-56 h-56 flex items-center justify-center border border-border-std rounded">
              <Loader2 size={20} className="animate-spin text-text-tertiary" />
            </div>
          )}
        </div>

        <div className="text-xs text-text-tertiary break-all bg-bg-cell border border-border-std rounded px-2 py-1.5 mb-3">
          {ficheUrl}
        </div>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={copyLink}
            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs rounded border border-border-std hover:bg-bg-light text-text-secondary"
          >
            <Link2 size={12} />
            {copied ? "Lien copie" : "Copier le lien"}
          </button>
          <a
            href={ficheUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs rounded bg-vinci-blue text-white hover:bg-vinci-blue/90"
          >
            <ExternalLink size={12} />
            Ouvrir la fiche
          </a>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Carnet de cables — onglet
// ---------------------------------------------------------------------------

function CableBookTab({ projectId }: { projectId: string }) {
  const [selectedExportId, setSelectedExportId] = useState<string>("");
  const [filterAval, setFilterAval] = useState<string>("");
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [isDownloading, setIsDownloading] = useState<boolean>(false);

  const { data: exports } = useQuery({
    queryKey: ["caneco", projectId],
    queryFn: () => listCaneco(projectId),
  });

  const lastExportId = exports?.[0]?.id;
  const effectiveExportId = selectedExportId || lastExportId || "";

  const { data: report, isLoading, isError } = useQuery({
    queryKey: ["cable-book", projectId, effectiveExportId, filterAval],
    queryFn: () => getCableBook(projectId, effectiveExportId, filterAval || undefined),
    enabled: !!effectiveExportId,
  });

  const filteredEntries = (report?.entries ?? []).filter((e) => {
    if (typeFilter && !e.type_cable.toLowerCase().includes(typeFilter.toLowerCase()))
      return false;
    return true;
  });

  async function handleExport() {
    if (!effectiveExportId) return;
    setIsDownloading(true);
    try {
      const { blob, filename } = await downloadCableBookExcel(
        projectId,
        effectiveExportId,
        filterAval || undefined
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } finally {
      setIsDownloading(false);
    }
  }

  if (!exports || exports.length === 0) {
    return (
      <div className="flex-1 min-h-0 overflow-auto p-6">
        <div className="border border-dashed border-border-std rounded p-8 text-center">
          <FileSpreadsheet size={28} className="mx-auto text-text-tertiary mb-2" />
          <p className="text-sm text-text-secondary">
            Aucun export CANECO disponible. Importez d'abord un export pour generer
            le carnet de cables.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 min-h-0 overflow-auto p-6 space-y-5">
      <div className="bg-vinci-blue/5 border border-vinci-blue/20 rounded p-3 text-xs text-vinci-blue">
        Le carnet de cables aggregre les lignes CANECO par type et section pour le
        chiffrage et les commandes. Les longueurs tiennent compte du nombre de
        cables paralleles (ex. 3X(1x150) = 3x la longueur de la ligne).
      </div>

      <div className="flex items-end gap-3 flex-wrap">
        <div>
          <label className="block text-xs text-text-tertiary mb-1">Export CANECO</label>
          <select
            value={effectiveExportId}
            onChange={(e) => setSelectedExportId(e.target.value)}
            className="text-xs border border-border-std rounded px-2 py-1.5 bg-white min-w-[200px]"
          >
            {exports.map((ex) => (
              <option key={ex.id} value={ex.id}>
                Indice {ex.indice} — {ex.file_name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-text-tertiary mb-1">
            Filtre tableau aval (optionnel)
          </label>
          <input
            type="text"
            value={filterAval}
            onChange={(e) => setFilterAval(e.target.value)}
            placeholder="Ex. TGBT, TES1..."
            className="text-xs border border-border-std rounded px-2 py-1.5 bg-white min-w-[180px]"
          />
        </div>
        <div>
          <label className="block text-xs text-text-tertiary mb-1">
            Filtre type cable
          </label>
          <input
            type="text"
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            placeholder="Ex. U1000R2V, CR1..."
            className="text-xs border border-border-std rounded px-2 py-1.5 bg-white min-w-[180px]"
          />
        </div>
        <button
          type="button"
          onClick={handleExport}
          disabled={isDownloading || !report}
          className={cn(
            "flex items-center gap-1.5 px-3 py-1.5 text-xs rounded transition-colors",
            "bg-vinci-blue text-white hover:bg-vinci-blue/90",
            "disabled:opacity-50 disabled:cursor-not-allowed"
          )}
        >
          <Download size={11} />
          {isDownloading ? "Generation..." : "Exporter Excel"}
        </button>
      </div>

      {isLoading && (
        <div className="text-sm text-text-tertiary">Calcul du carnet en cours...</div>
      )}
      {isError && (
        <div className="text-sm text-status-warn">
          Erreur lors du chargement du carnet de cables.
        </div>
      )}

      {report && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <KpiCard
              label="Longueur totale projet"
              value={`${formatMeters(report.longueur_totale_projet_m)} m`}
              color="text-vinci-blue"
              bg="bg-vinci-blue/5 border-vinci-blue/20"
            />
            <KpiCard
              label="Types de cables"
              value={report.nb_types_cables_distincts}
              color="text-text-primary"
              bg="bg-bg-cell border-border-std"
            />
            <KpiCard
              label="Lignes CANECO"
              value={report.nb_lignes_caneco_traitees}
              color="text-text-primary"
              bg="bg-bg-cell border-border-std"
            />
            <KpiCard
              label="Lignes affichees"
              value={filteredEntries.length}
              color="text-text-primary"
              bg="bg-bg-cell border-border-std"
            />
          </div>

          {report.top5.length > 0 && (
            <div className="border border-border-std rounded p-4 bg-white">
              <h4 className="text-xs font-semibold text-text-tertiary uppercase tracking-wide mb-3">
                Top 5 des cables les plus consommes
              </h4>
              <div className="space-y-1.5">
                {report.top5.map((e, i) => (
                  <div
                    key={`${e.type_cable}-${e.cable_caneco}`}
                    className="flex items-center justify-between text-xs"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-text-tertiary font-mono w-4">#{i + 1}</span>
                      <span className="text-text-primary">{e.type_cable}</span>
                      <span className="font-mono bg-bg-cell px-1.5 py-0.5 rounded text-text-secondary">
                        {e.cable_caneco}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-text-primary font-medium">
                        {formatMeters(e.longueur_totale_m)} m
                      </span>
                      <span className="text-text-tertiary w-12 text-right">
                        {e.pourcentage_du_total.toFixed(1)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="border border-border-std rounded overflow-hidden">
            <div className="px-4 py-2 bg-bg-cell border-b border-border-std">
              <h4 className="text-xs font-semibold text-text-tertiary uppercase tracking-wide">
                Sommaire des cables ({filteredEntries.length} ligne
                {filteredEntries.length !== 1 ? "s" : ""})
              </h4>
            </div>
            <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
              <table className="w-full text-xs">
                <thead className="sticky top-0 z-10" style={{ backgroundColor: "#001E50" }}>
                  <tr>
                    <th className="px-3 py-2 text-left font-medium text-white/80">
                      Type cable
                    </th>
                    <th className="px-3 py-2 text-left font-medium text-white/80">
                      Section CANECO
                    </th>
                    <th className="px-3 py-2 text-right font-medium text-white/80 w-[100px]">
                      Section (mm²)
                    </th>
                    <th className="px-3 py-2 text-right font-medium text-white/80 w-[140px]">
                      Long. totale (m)
                    </th>
                    <th className="px-3 py-2 text-right font-medium text-white/80 w-[110px] hidden sm:table-cell">
                      Nb conducteurs
                    </th>
                    <th className="px-3 py-2 text-right font-medium text-white/80 w-[110px] hidden sm:table-cell">
                      Occurrences
                    </th>
                    <th className="px-3 py-2 text-right font-medium text-white/80 w-[100px]">
                      % projet
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filteredEntries.length === 0 ? (
                    <tr>
                      <td
                        colSpan={7}
                        className="px-3 py-6 text-center text-text-tertiary"
                      >
                        Aucun cable ne correspond aux filtres actifs.
                      </td>
                    </tr>
                  ) : (
                    filteredEntries.map((e, i) => (
                      <CableBookRow
                        key={`${e.type_cable}-${e.cable_caneco}`}
                        entry={e}
                        striped={i % 2 === 1}
                      />
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {Object.keys(report.longueur_par_aval).length > 0 && (
            <div className="border border-border-std rounded p-4 bg-white">
              <h4 className="text-xs font-semibold text-text-tertiary uppercase tracking-wide mb-3">
                Longueur par tableau aval / lot
              </h4>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
                {Object.entries(report.longueur_par_aval)
                  .sort(([, a], [, b]) => b - a)
                  .map(([aval, lg]) => (
                    <div
                      key={aval}
                      className="flex items-center justify-between bg-bg-cell rounded px-2 py-1.5 text-xs"
                    >
                      <span className="font-mono text-text-secondary truncate">
                        {aval}
                      </span>
                      <span className="text-text-primary font-medium">
                        {formatMeters(lg)} m
                      </span>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function CableBookRow({ entry, striped }: { entry: CableBookEntry; striped: boolean }) {
  return (
    <tr
      className={cn(
        "border-t border-border-std hover:bg-vinci-blue/5 transition-colors",
        striped ? "bg-bg-cell/40" : "bg-white"
      )}
    >
      <td className="px-3 py-2 text-text-primary">{entry.type_cable}</td>
      <td className="px-3 py-2 font-mono text-text-primary">
        <span className="bg-bg-cell px-1.5 py-0.5 rounded border border-border-std">
          {entry.cable_caneco}
        </span>
      </td>
      <td className="px-3 py-2 text-right text-text-secondary">
        {entry.section_mm2 != null ? entry.section_mm2 : "—"}
      </td>
      <td className="px-3 py-2 text-right text-text-primary font-medium">
        {formatMeters(entry.longueur_totale_m)}
      </td>
      <td className="px-3 py-2 text-right text-text-tertiary hidden sm:table-cell">
        {entry.nb_conducteurs > 0 ? entry.nb_conducteurs : "—"}
        {entry.nb_circuits_paralleles > 1 && (
          <span className="text-[10px] text-text-tertiary ml-1">
            (x{entry.nb_circuits_paralleles})
          </span>
        )}
      </td>
      <td className="px-3 py-2 text-right text-text-tertiary hidden sm:table-cell">
        {entry.nb_occurrences}
      </td>
      <td className="px-3 py-2 text-right text-text-primary font-medium">
        {entry.pourcentage_du_total.toFixed(2)}%
      </td>
    </tr>
  );
}

function KpiCard({
  label,
  value,
  color,
  bg,
}: {
  label: string;
  value: string | number;
  color: string;
  bg: string;
}) {
  return (
    <div className={cn("border rounded p-3 text-center", bg)}>
      <div className={cn("text-xl font-bold", color)}>{value}</div>
      <div className="text-[11px] font-medium text-text-secondary mt-0.5">{label}</div>
    </div>
  );
}

function formatMeters(m: number): string {
  return new Intl.NumberFormat("fr-FR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(m);
}
