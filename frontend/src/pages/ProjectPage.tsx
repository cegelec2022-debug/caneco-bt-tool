import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ChevronFirst,
  ChevronLast,
  ChevronLeft,
  ChevronRight,
  Download,
  FileSpreadsheet,
  Pencil,
  Search,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  deleteCaneco,
  downloadCanecoExcel,
  getCaneco,
  listCaneco,
  updateCanecoIndice,
  uploadCaneco,
} from "@/api/caneco";
import { deleteProject, getProject, updateProject } from "@/api/projects";
import { cn } from "@/lib/utils";
import type { CanecoExport, CanecoExportDetail, CanecoLine, ProjectUpdate } from "@/types";

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
  { id: "tableaux", label: "Tableaux" },
  { id: "doe", label: "DOE" },
] as const;

type TabId = (typeof TABS)[number]["id"];

const STATUS_OPTIONS = ["actif", "en_attente", "archive"];

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

        {activeTab === "tableaux" && (
          <div className="flex-1 min-h-0 overflow-auto p-6">
            <div className="text-sm text-text-tertiary">
              Module 3 — Bordereau / CPS / Verification (disponible en V1.1)
            </div>
          </div>
        )}
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
