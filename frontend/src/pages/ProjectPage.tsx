import { useQuery } from "@tanstack/react-query";
import { ChevronLeft } from "lucide-react";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getProject } from "@/api/projects";
import { cn } from "@/lib/utils";

const TABS = [
  { id: "overview", label: "Vue d'ensemble" },
  { id: "studies", label: "Etudes" },
  { id: "tableaux", label: "Tableaux" },
  { id: "doe", label: "DOE" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export default function ProjectPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabId>("overview");

  const { data: project, isLoading, isError } = useQuery({
    queryKey: ["project", id],
    queryFn: () => getProject(id!),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="p-6 text-sm text-text-tertiary">Chargement...</div>
    );
  }

  if (isError || !project) {
    return (
      <div className="p-6 text-sm text-status-warn">Projet introuvable.</div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-6 py-4 border-b border-border-std bg-white">
        <button
          onClick={() => navigate("/projects")}
          className="flex items-center gap-1 text-xs text-text-tertiary hover:text-text-primary mb-3 transition-colors"
        >
          <ChevronLeft size={14} />
          Projets
        </button>
        <div className="flex items-start justify-between">
          <div>
            <span className="text-xs font-mono text-text-tertiary">{project.code}</span>
            <h2 className="text-lg font-semibold text-text-primary mt-0.5">{project.name}</h2>
            {project.client && (
              <p className="text-sm text-text-secondary">{project.client}</p>
            )}
          </div>
          <span className="text-xs px-2 py-1 rounded bg-bg-cell text-text-tertiary">
            {project.status}
          </span>
        </div>
      </div>

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

      <div className="flex-1 overflow-auto p-6">
        {activeTab === "overview" && (
          <div className="max-w-lg space-y-4">
            <div className="bg-white border border-border-std rounded p-4">
              <h3 className="text-xs font-semibold text-text-tertiary uppercase tracking-wide mb-3">
                Informations projet
              </h3>
              <dl className="space-y-2 text-sm">
                <div className="flex gap-4">
                  <dt className="w-28 text-text-tertiary shrink-0">Code</dt>
                  <dd className="text-text-primary font-mono">{project.code}</dd>
                </div>
                <div className="flex gap-4">
                  <dt className="w-28 text-text-tertiary shrink-0">Nom</dt>
                  <dd className="text-text-primary">{project.name}</dd>
                </div>
                {project.client && (
                  <div className="flex gap-4">
                    <dt className="w-28 text-text-tertiary shrink-0">Client</dt>
                    <dd className="text-text-primary">{project.client}</dd>
                  </div>
                )}
                {project.agency && (
                  <div className="flex gap-4">
                    <dt className="w-28 text-text-tertiary shrink-0">Agence</dt>
                    <dd className="text-text-primary">{project.agency}</dd>
                  </div>
                )}
                {project.description && (
                  <div className="flex gap-4">
                    <dt className="w-28 text-text-tertiary shrink-0">Description</dt>
                    <dd className="text-text-primary">{project.description}</dd>
                  </div>
                )}
                <div className="flex gap-4">
                  <dt className="w-28 text-text-tertiary shrink-0">Statut</dt>
                  <dd className="text-text-primary">{project.status}</dd>
                </div>
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
    </div>
  );
}
