import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, Pencil, Trash2, X } from "lucide-react";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { deleteProject, getProject, updateProject } from "@/api/projects";
import { cn } from "@/lib/utils";
import type { ProjectUpdate } from "@/types";

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
          <div className="text-sm text-text-tertiary">
            Module 2 — Import CANECO BT (disponible en V1.1)
          </div>
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

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex gap-4">
      <dt className="w-28 text-text-tertiary shrink-0">{label}</dt>
      <dd className="text-text-primary">{value}</dd>
    </div>
  );
}
