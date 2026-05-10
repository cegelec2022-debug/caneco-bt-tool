import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ChevronLeft,
  ChevronRight,
  FileSpreadsheet,
  Pencil,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { deleteCaneco, getCaneco, listCaneco, uploadCaneco } from "@/api/caneco";
import { deleteProject, getProject, updateProject } from "@/api/projects";
import { cn } from "@/lib/utils";
import type { CanecoExport, CanecoExportDetail, CanecoLine, ProjectUpdate } from "@/types";

const TABS = [
  { id: "overview", label: "Vue d'ensemble" },
  { id: "studies", label: "Etudes" },
  { id: "tableaux", label: "Tableaux" },
  { id: "doe", label: "DOE" },
] as const;

type TabId = (typeof TABS)[number]["id"];

const STATUS_OPTIONS = ["actif", "en_attente", "archivé"];

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
        "Erreur lors de la mise à jour.";
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
    <div className="flex flex-col h-full">
      {/* En-tête projet */}
      <div className="px-6 py-4 border-b border-border-std bg-white">
        <button
          onClick={() => navigate("/projects")}
          className="flex items-center gap-1 text-xs text-text-tertiary hover:text-text-primary mb-3 transition-colors"
        >
          <ChevronLeft size={14} />
          Projets
        </button>

        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <span className="text-xs font-mono text-text-tertiary">{project.code}</span>
            <h2 className="text-lg font-semibold text-text-primary mt-0.5 truncate">
              {project.name}
            </h2>
            {project.client && (
              <p className="text-sm text-text-secondary">{project.client}</p>
            )}
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <span
              className={cn(
                "text-xs px-2 py-1 rounded",
                project.status === "actif" && "bg-green-100 text-status-ok",
                project.status === "archivé" && "bg-gray-100 text-text-tertiary",
                project.status === "en_attente" && "bg-yellow-100 text-yellow-700",
                !["actif", "archivé", "en_attente"].includes(project.status) &&
                  "bg-bg-cell text-text-tertiary"
              )}
            >
              {project.status}
            </span>
            <button
              onClick={openEdit}
              title="Modifier le projet"
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs border border-border-std rounded hover:bg-bg-cell transition-colors text-text-secondary"
            >
              <Pencil size={13} />
              Modifier
            </button>
            <button
              onClick={() => setShowDeleteConfirm(true)}
              title="Supprimer le projet"
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs border border-red-200 rounded hover:bg-red-50 transition-colors text-status-warn"
            >
              <Trash2 size={13} />
              Supprimer
            </button>
          </div>
        </div>
      </div>

      {/* Onglets */}
      <div className="border-b border-border-std bg-white px-6">
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

      {/* Contenu onglets */}
      <div className="flex-1 overflow-auto p-6">
        {activeTab === "overview" && (
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
                <Row label="Créé le" value={formatDate(project.created_at)} />
                <Row label="Modifié le" value={formatDate(project.updated_at)} />
              </dl>
            </div>
          </div>
        )}

        {activeTab === "studies" && (
          <EtudesTab projectId={id!} />
        )}

        {activeTab === "tableaux" && (
          <div className="text-sm text-text-tertiary">
            Module 3 — Bordereau / CPS / Vérification (disponible en V1.1)
          </div>
        )}
        {activeTab === "doe" && (
          <div className="text-sm text-text-tertiary">
            Module 5 — Génération DOE (disponible en V1.1)
          </div>
        )}
      </div>

      {/* Modal modifier */}
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

              {editError && (
                <p className="text-xs text-status-warn">{editError}</p>
              )}

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

      {/* Modal confirmation suppression */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded w-full max-w-sm shadow-lg p-6">
            <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center mb-4">
              <Trash2 size={18} className="text-status-warn" />
            </div>
            <h3 className="font-semibold text-text-primary mb-2">Supprimer le projet</h3>
            <p className="text-sm text-text-secondary mb-1">
              Vous êtes sur le point de supprimer{" "}
              <span className="font-medium text-text-primary">{project.name}</span>.
            </p>
            <p className="text-xs text-text-tertiary mb-6">
              Cette action est irréversible. Toutes les données associées seront perdues.
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
                {isDeleting ? "Suppression..." : "Supprimer définitivement"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Onglet Etudes — upload + tableau des données
// ---------------------------------------------------------------------------

function EtudesTab({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const [selectedExportId, setSelectedExportId] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [showUpload, setShowUpload] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const { data: exports, isLoading: loadingExports } = useQuery({
    queryKey: ["caneco", projectId],
    queryFn: () => listCaneco(projectId),
  });

  const { data: detail, isLoading: loadingDetail } = useQuery({
    queryKey: ["caneco-detail", projectId, selectedExportId, page],
    queryFn: () => getCaneco(projectId, selectedExportId!, page, 50),
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

  function handleSelectExport(exp: CanecoExport) {
    setSelectedExportId(exp.id);
    setPage(1);
    setShowUpload(false);
  }

  if (loadingExports) {
    return <div className="text-sm text-text-tertiary">Chargement...</div>;
  }

  const hasExports = exports && exports.length > 0;

  return (
    <div className="space-y-4">
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
          onClick={() => {
            setShowUpload((v) => !v);
            setSelectedExportId(null);
          }}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-vinci-blue text-white rounded hover:bg-vinci-blue/90 transition-colors"
        >
          <Upload size={13} />
          Importer un fichier CANECO
        </button>
      </div>

      {/* Zone upload */}
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

      {/* Liste des imports */}
      {!hasExports && !showUpload && (
        <EmptyState onUpload={() => setShowUpload(true)} />
      )}

      {hasExports && (
        <div className="grid grid-cols-1 gap-3">
          {exports.map((exp) => (
            <ExportCard
              key={exp.id}
              exp={exp}
              isSelected={selectedExportId === exp.id}
              onSelect={() => handleSelectExport(exp)}
              onDelete={() => setConfirmDeleteId(exp.id)}
            />
          ))}
        </div>
      )}

      {/* Tableau des lignes */}
      {selectedExportId && (
        <LinesTable
          detail={detail ?? null}
          isLoading={loadingDetail}
          page={page}
          onPageChange={setPage}
        />
      )}

      {/* Modal suppression export */}
      {confirmDeleteId && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded w-full max-w-sm shadow-lg p-6">
            <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center mb-4">
              <Trash2 size={18} className="text-status-warn" />
            </div>
            <h3 className="font-semibold text-text-primary mb-2">Supprimer l'import</h3>
            <p className="text-sm text-text-secondary mb-6">
              Cette action supprimera l'import et toutes ses lignes de manière irréversible.
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
    </div>
  );
}

// ---------------------------------------------------------------------------
// Carte d'un export
// ---------------------------------------------------------------------------

function ExportCard({
  exp,
  isSelected,
  onSelect,
  onDelete,
}: {
  exp: CanecoExport;
  isSelected: boolean;
  onSelect: () => void;
  onDelete: () => void;
}) {
  const statusConfig = {
    parsed: { label: "Parsé", cls: "bg-green-100 text-status-ok" },
    parsing: { label: "En cours...", cls: "bg-yellow-100 text-yellow-700" },
    error: { label: "Erreur", cls: "bg-red-100 text-status-warn" },
  } as const;

  const cfg = statusConfig[exp.status] ?? { label: exp.status, cls: "bg-bg-cell text-text-tertiary" };

  return (
    <div
      className={cn(
        "border rounded p-4 cursor-pointer transition-colors group",
        isSelected
          ? "border-vinci-blue bg-blue-50/50"
          : "border-border-std bg-white hover:border-vinci-blue/40"
      )}
      onClick={onSelect}
    >
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <FileSpreadsheet size={18} className="text-text-tertiary shrink-0" />
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-vinci-blue text-white">
                Indice {exp.indice}
              </span>
              <span className={cn("text-xs px-2 py-0.5 rounded", cfg.cls)}>{cfg.label}</span>
              {exp.line_count !== null && (
                <span className="text-xs text-text-tertiary">
                  {exp.line_count} ligne{exp.line_count > 1 ? "s" : ""}
                </span>
              )}
            </div>
            <p className="text-xs text-text-tertiary mt-1 truncate">{exp.file_name}</p>
          </div>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <span className="text-xs text-text-tertiary">{formatDateTime(exp.uploaded_at)}</span>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="opacity-0 group-hover:opacity-100 transition-opacity text-text-tertiary hover:text-status-warn"
            title="Supprimer cet import"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tableau des lignes
// ---------------------------------------------------------------------------

const COLUMNS: { key: keyof CanecoLine; label: string; cls?: string }[] = [
  { key: "repere", label: "Repère", cls: "font-mono" },
  { key: "designation", label: "Désignation" },
  { key: "style", label: "Style" },
  { key: "nb_recepteurs", label: "Nb. réc." },
  { key: "ib", label: "Ib (A)" },
  { key: "longueur", label: "Long. (m)" },
  { key: "type_cable", label: "Type câble" },
  { key: "cable", label: "Section" },
  { key: "calibre", label: "Calibre (A)" },
  { key: "icu", label: "Icu (kA)" },
];

function LinesTable({
  detail,
  isLoading,
  page,
  onPageChange,
}: {
  detail: CanecoExportDetail | null;
  isLoading: boolean;
  page: number;
  onPageChange: (p: number) => void;
}) {
  if (isLoading) {
    return (
      <div className="mt-4 border border-border-std rounded bg-white p-8 text-center text-sm text-text-tertiary">
        Chargement des données...
      </div>
    );
  }

  if (!detail) return null;

  const { lines, total, total_pages } = detail;

  return (
    <div className="mt-4 border border-border-std rounded bg-white overflow-hidden">
      {/* En-tête du tableau */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border-std bg-bg-cell">
        <p className="text-xs font-semibold text-text-secondary">
          {total} départ{total > 1 ? "s" : ""} — indice{" "}
          <span className="font-mono">{detail.export.indice}</span>
        </p>
        {total_pages > 1 && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-text-tertiary">
              Page {page} / {total_pages}
            </span>
            <button
              onClick={() => onPageChange(Math.max(1, page - 1))}
              disabled={page <= 1}
              className="p-1 rounded border border-border-std hover:bg-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft size={14} />
            </button>
            <button
              onClick={() => onPageChange(Math.min(total_pages, page + 1))}
              disabled={page >= total_pages}
              className="p-1 rounded border border-border-std hover:bg-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronRight size={14} />
            </button>
          </div>
        )}
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border-std bg-bg-cell/50">
              {COLUMNS.map((col) => (
                <th
                  key={col.key}
                  className="text-left px-3 py-2 text-text-tertiary font-medium whitespace-nowrap"
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border-std">
            {lines.map((line) => (
              <tr key={line.id} className="hover:bg-bg-light transition-colors">
                {COLUMNS.map((col) => {
                  const val = line[col.key];
                  const display =
                    val === null || val === undefined
                      ? <span className="text-text-tertiary">—</span>
                      : typeof val === "number"
                      ? formatNum(val)
                      : String(val);
                  return (
                    <td
                      key={col.key}
                      className={cn("px-3 py-2 whitespace-nowrap text-text-primary", col.cls)}
                    >
                      {display}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function formatNum(n: number): string {
  if (Number.isInteger(n)) return String(n);
  return n.toLocaleString("fr-FR", { maximumFractionDigits: 2 });
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
      setError("Format non supporté. Utilisez un fichier .xls ou .xlsx.");
      return;
    }
    if (f.size > 50 * 1024 * 1024) {
      setError("Fichier trop volumineux (max 50 Mo).");
      return;
    }
    setFile(f);
    setError(null);
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
      setError("Veuillez sélectionner un fichier.");
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
      <h4 className="text-sm font-semibold text-text-primary mb-4">Importer un export CANECO BT</h4>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Zone drag & drop */}
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
            className={cn(
              "mx-auto mb-2",
              file ? "text-green-600" : "text-text-tertiary"
            )}
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
              <p className="text-sm text-text-secondary">
                Glissez votre fichier XLS/XLSX ici
              </p>
              <p className="text-xs text-text-tertiary mt-1">ou cliquez pour parcourir</p>
            </div>
          )}
        </div>

        {/* Indice */}
        <div className="flex items-center gap-3">
          <label className="text-sm text-text-secondary shrink-0 w-32">
            Indice de révision
          </label>
          <input
            type="text"
            value={indice}
            onChange={(e) => setIndice(e.target.value.toUpperCase())}
            maxLength={10}
            placeholder="A"
            className="w-24 border border-border-std rounded px-3 py-2 text-sm font-mono uppercase focus:outline-none focus:border-vinci-blue"
          />
          <span className="text-xs text-text-tertiary">
            ex. A, B, B2, C…
          </span>
        </div>

        {/* Erreur */}
        {error && (
          <div className="flex items-start gap-2 text-xs text-status-warn bg-red-50 border border-red-200 rounded px-3 py-2">
            <span className="mt-0.5 shrink-0">&#9888;</span>
            <span>{error}</span>
          </div>
        )}

        {/* Boutons */}
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
// État vide
// ---------------------------------------------------------------------------

function EmptyState({ onUpload }: { onUpload: () => void }) {
  return (
    <div className="border-2 border-dashed border-border-std rounded p-12 text-center">
      <FileSpreadsheet size={40} className="mx-auto mb-3 text-text-tertiary" />
      <p className="text-sm font-medium text-text-primary mb-1">
        Aucun export CANECO importé
      </p>
      <p className="text-xs text-text-tertiary mb-4">
        Importez votre fichier export CANECO BT (.xls ou .xlsx) pour visualiser les départs.
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
