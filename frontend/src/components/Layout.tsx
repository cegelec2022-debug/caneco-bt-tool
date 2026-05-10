import { FolderOpen, LayoutDashboard, LogOut } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";

const ROLE_LABELS: Record<string, string> = {
  BE: "Bureau d'Etudes",
  chef_chantier: "Chef de Chantier",
  RA: "Responsable Affaires",
  admin: "Administrateur",
};

export default function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className="h-full flex flex-col">
      <header className="bg-vinci-blue text-white px-6 py-3 flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Valorisation des données CANECO BT</h1>
          <p className="text-xs text-white/70">Actemium Cegelec — VINCI Energies</p>
        </div>
        <img src="/logo-vinci.png" alt="VINCI Energies" className="h-10 object-contain" />
      </header>

      <div className="flex flex-1 overflow-hidden">
        <nav className="w-56 bg-white border-r border-border-std flex flex-col shrink-0">
          <div className="flex-1 py-4 space-y-1 px-3">
            <NavLink
              to="/projects"
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2 px-3 py-2 rounded text-sm font-medium transition-colors",
                  isActive
                    ? "bg-vinci-blue text-white"
                    : "text-text-secondary hover:bg-bg-cell"
                )
              }
            >
              <FolderOpen size={16} />
              Projets
            </NavLink>

            {user && (user.role === "RA" || user.role === "admin") && (
              <NavLink
                to="/dashboard"
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-2 px-3 py-2 rounded text-sm font-medium transition-colors",
                    isActive
                      ? "bg-vinci-blue text-white"
                      : "text-text-secondary hover:bg-bg-cell"
                  )
                }
              >
                <LayoutDashboard size={16} />
                Tableau de bord
              </NavLink>
            )}
          </div>

          <div className="border-t border-border-std p-3">
            <div className="text-xs text-text-tertiary mb-1">{user?.full_name}</div>
            <div className="text-xs text-text-tertiary mb-3">
              {user ? ROLE_LABELS[user.role] ?? user.role : ""}
            </div>
            <button
              onClick={logout}
              className="flex items-center gap-2 text-xs text-text-secondary hover:text-vinci-red transition-colors"
            >
              <LogOut size={14} />
              Déconnexion
            </button>
          </div>
        </nav>

        <main className="flex-1 min-h-0 overflow-hidden bg-bg-light flex flex-col">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
