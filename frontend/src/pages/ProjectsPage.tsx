import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FolderPlus, X } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createProject, listProjects } from "@/api/projects";
import type { ProjectCreate } from "@/types";

const STATUS_COLORS: Record<string, string> = {
  actif: "bg-green-100 text-status-ok",
  archivé: "bg-gray-100 text-text-tertiary",
  en_attente: "bg-yellow-100 text-yellow-700",
};

export default function ProjectsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState<ProjectCreate>({
    code: "",
    name: "",
    client: "",
    agency: "",
    status: "actif",
  });
  const [formError, setFormError] = useState<string | null>(null);

  const { data: projects = [], isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: listProjects,
  });

  const { mutate: create, isPending } = useMutation({
    mutationFn: createProject,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setShowForm(false);
      setFormData({ code: "", name: "", client: "", agency: "", status: "actif" });
      setFormError(null);
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Erreur lors de la création.";
      setFormError(msg);
    },
  });

  function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!formData.code.trim() || !formData.name.trim()) {
      setFormError("Le code et le nom sont obligatoires.");
      return;
    }
    create(formData);
  }

  return (
    <div className="flex-1 min-h-0 overflow-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold text-text-primary">Projets</h2>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 bg-vinci-blue text-white px-4 py-2 rounded text-sm font-medium hover:bg-vinci-blue/90 transition-colors"
        >
          <FolderPlus size={16} />
          Nouveau projet
        </button>
      </div>

      {isLoading && (
        <div className="text-sm text-text-tertiary">Chargement...</div>
      )}

      {!isLoading && projects.length === 0 && (
        <div className="text-center py-16 text-text-tertiary text-sm">
          Aucun projet. Créez votre premier projet.
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {projects.map((project) => (
          <button
            key={project.id}
            onClick={() => navigate(`/projects/${project.id}`)}
            className="text-left bg-white border border-border-std rounded p-4 hover:border-vinci-blue transition-colors"
          >
            <div className="flex items-start justify-between mb-2">
              <span className="text-xs font-mono text-text-tertiary">{project.code}</span>
              <span
                className={`text-xs px-2 py-0.5 rounded-full ${STATUS_COLORS[project.status] ?? "bg-gray-100 text-text-tertiary"}`}
              >
                {project.status}
              </span>
            </div>
            <h3 className="font-medium text-text-primary text-sm mb-1">{project.name}</h3>
            {project.client && (
              <p className="text-xs text-text-secondary">{project.client}</p>
            )}
            {project.agency && (
              <p className="text-xs text-text-tertiary">{project.agency}</p>
            )}
          </button>
        ))}
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded w-full max-w-md">
            <div className="flex items-center justify-between px-5 py-4 border-b border-border-std">
              <h3 className="font-semibold text-text-primary">Nouveau projet</h3>
              <button onClick={() => setShowForm(false)} className="text-text-tertiary hover:text-text-primary">
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCreate} className="p-5 space-y-4">
              <div>
                <label className="block text-sm text-text-secondary mb-1">Code *</label>
                <input
                  type="text"
                  value={formData.code}
                  onChange={(e) => setFormData((d) => ({ ...d, code: e.target.value }))}
                  className="w-full border border-border-std rounded px-3 py-2 text-sm focus:outline-none focus:border-vinci-blue font-mono"
                  placeholder="DACHSER-L3"
                />
              </div>
              <div>
                <label className="block text-sm text-text-secondary mb-1">Nom *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData((d) => ({ ...d, name: e.target.value }))}
                  className="w-full border border-border-std rounded px-3 py-2 text-sm focus:outline-none focus:border-vinci-blue"
                  placeholder="DACHSER Lot 3 - Électricité"
                />
              </div>
              <div>
                <label className="block text-sm text-text-secondary mb-1">Client</label>
                <input
                  type="text"
                  value={formData.client ?? ""}
                  onChange={(e) => setFormData((d) => ({ ...d, client: e.target.value }))}
                  className="w-full border border-border-std rounded px-3 py-2 text-sm focus:outline-none focus:border-vinci-blue"
                />
              </div>
              <div>
                <label className="block text-sm text-text-secondary mb-1">Agence</label>
                <input
                  type="text"
                  value={formData.agency ?? ""}
                  onChange={(e) => setFormData((d) => ({ ...d, agency: e.target.value }))}
                  className="w-full border border-border-std rounded px-3 py-2 text-sm focus:outline-none focus:border-vinci-blue"
                />
              </div>

              {formError && (
                <p className="text-xs text-status-warn">{formError}</p>
              )}

              <div className="flex gap-3 justify-end pt-2">
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="px-4 py-2 text-sm text-text-secondary border border-border-std rounded hover:bg-bg-cell transition-colors"
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  disabled={isPending}
                  className="px-4 py-2 text-sm bg-vinci-blue text-white rounded hover:bg-vinci-blue/90 transition-colors disabled:opacity-50"
                >
                  {isPending ? "Création..." : "Créer"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
