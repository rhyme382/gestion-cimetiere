import { NavLink } from "react-router-dom";
import {
  LayoutDashboard, Building2, MapPin, FileText, Users, Bell, Search, HardDrive, Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Tableau de bord" },
  { to: "/cimetieres", icon: Building2, label: "Cimetières" },
  { to: "/emplacements", icon: MapPin, label: "Emplacements" },
  { to: "/concessions", icon: FileText, label: "Concessions" },
  { to: "/defunts", icon: Users, label: "Défunts" },
  { to: "/alertes", icon: Bell, label: "Alertes" },
  { to: "/recherche", icon: Search, label: "Recherche" },
];

const bottomItems = [
  { to: "/sauvegardes", icon: HardDrive, label: "Sauvegardes" },
  { to: "/parametres", icon: Settings, label: "Paramètres" },
];

export function Sidebar() {
  return (
    <aside className="flex h-full w-56 flex-col bg-sidebar text-sidebar-foreground">
      <div className="flex items-center gap-2 px-4 py-5 border-b border-sidebar-border">
        <div className="h-8 w-8 rounded-md bg-sidebar-active flex items-center justify-center text-white font-bold text-sm">GC</div>
        <div>
          <p className="text-sm font-semibold text-white leading-tight">Gestion Cimetière</p>
          <p className="text-xs text-sidebar-foreground/60 leading-tight">Administration</p>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-0.5">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                isActive
                  ? "bg-sidebar-active text-sidebar-active-foreground font-medium"
                  : "text-sidebar-foreground/80 hover:bg-white/10 hover:text-white"
              )
            }
          >
            <Icon className="h-4 w-4 shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="px-2 py-3 border-t border-sidebar-border space-y-0.5">
        {bottomItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                isActive
                  ? "bg-sidebar-active text-sidebar-active-foreground font-medium"
                  : "text-sidebar-foreground/80 hover:bg-white/10 hover:text-white"
              )
            }
          >
            <Icon className="h-4 w-4 shrink-0" />
            {label}
          </NavLink>
        ))}
      </div>
    </aside>
  );
}
