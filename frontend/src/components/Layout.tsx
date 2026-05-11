import { FolderOpen, LayoutDashboard, LogOut, Menu, X } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
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
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();

  // Ferme le drawer mobile a chaque navigation
  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  return (
    <div className="h-screen overflow-hidden flex flex-col">
      <header className="bg-vinci-blue text-white px-3 sm:px-6 py-3 flex items-center justify-between shrink-0 gap-3">
        <button
          type="button"
          aria-label="Ouvrir le menu"
          onClick={() => setMenuOpen(true)}
          className="md:hidden p-1.5 rounded hover:bg-white/10"
        >
          <Menu size={20} />
        </button>
        <div className="min-w-0 flex-1">
          <h1 className="text-sm sm:text-lg font-semibold tracking-tight truncate">
            <span className="hidden sm:inline">Valorisation des données </span>CANECO BT
          </h1>
          <p className="text-[10px] sm:text-xs text-white/70 truncate">
            Actemium Cegelec — VINCI Energies
          </p>
        </div>
        <img
          src="/logo-vinci.png"
          alt="VINCI Energies"
          className="h-7 sm:h-10 object-contain shrink-0"
        />
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar : drawer sur mobile, fixe sur desktop */}
        <Sidebar
          user={user}
          logout={logout}
          mobileOpen={menuOpen}
          onClose={() => setMenuOpen(false)}
        />

        <main className="flex-1 min-h-0 overflow-hidden bg-bg-light flex flex-col">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function Sidebar({
  user,
  logout,
  mobileOpen,
  onClose,
}: {
  user: ReturnType<typeof useAuth>["user"];
  logout: () => void;
  mobileOpen: boolean;
  onClose: () => void;
}) {
  const links = (
    <>
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
    </>
  );

  const userBlock = (
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
  );

  return (
    <>
      {/* Sidebar fixe sur desktop (md+) */}
      <nav className="hidden md:flex w-56 bg-white border-r border-border-std flex-col shrink-0">
        <div className="flex-1 py-4 space-y-1 px-3">{links}</div>
        {userBlock}
      </nav>

      {/* Drawer mobile : overlay + tiroir glissant */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/40 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}
      <nav
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-border-std flex flex-col md:hidden",
          "transition-transform duration-200 ease-out",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
        aria-hidden={!mobileOpen}
      >
        <div className="flex items-center justify-between px-3 py-3 border-b border-border-std bg-vinci-blue text-white">
          <span className="text-sm font-semibold">Menu</span>
          <button
            type="button"
            onClick={onClose}
            aria-label="Fermer le menu"
            className="p-1 rounded hover:bg-white/10"
          >
            <X size={18} />
          </button>
        </div>
        <div className="flex-1 py-4 space-y-1 px-3 overflow-y-auto">{links}</div>
        {userBlock}
      </nav>
    </>
  );
}
