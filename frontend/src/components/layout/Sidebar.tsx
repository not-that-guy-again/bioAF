"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NavItem } from "./NavItem";
import { getCurrentUser } from "@/lib/auth";

const navItems = [
  { label: "Home", href: "/", icon: "home", active: true },
  { label: "Experiments", href: "/experiments", icon: "flask", active: true },
  { label: "Projects", href: "/projects", icon: "folder", active: true },
  { label: "Data", href: "/data", icon: "database", active: true },
  { label: "Compute", href: "/compute", icon: "server", active: true },
  { label: "Pipeline Catalog", href: "/pipelines", icon: "workflow", active: true, compBioOnly: true },
  { label: "Pipeline Runs", href: "/pipelines/runs", icon: "play", active: true, compBioOnly: true },
  { label: "Packages", href: "/packages", icon: "package", active: true, compBioOnly: true },
  { label: "Environments", href: "/environments", icon: "layers", active: true, compBioOnly: true },
  { label: "Templates", href: "/notebooks/templates", icon: "notebook", active: true, compBioOnly: true },
  { label: "Results", href: "/results", icon: "chart", active: true },
  { label: "Reference Data", href: "/references", icon: "archive", active: true },
  { label: "Components", href: "/components", icon: "puzzle", active: true },
  { label: "Activity Feed", href: "/activity", icon: "activity", active: true },
  { label: "Templates", href: "/admin/templates", icon: "template", active: true, adminOnly: true },
  { label: "Users & Roles", href: "/admin/users", icon: "users", active: true, adminOnly: true },
  { label: "Backup & Recovery", href: "/admin/backups", icon: "shield", active: true, adminOnly: true },
  { label: "Cost Center", href: "/admin/costs", icon: "dollar", active: true, adminOnly: true },
  { label: "Access Logs", href: "/admin/access-logs", icon: "log", active: true, adminOnly: true },
  { label: "Settings", href: "/admin/settings", icon: "settings", active: true, adminOnly: true },
];

export function Sidebar() {
  const pathname = usePathname();
  const user = getCurrentUser();
  const isAdmin = user?.role === "admin";
  const isCompBio = user?.role === "comp_bio";
  const canSeePipelines = isAdmin || isCompBio;

  return (
    <aside className="w-64 bg-gray-900 text-white min-h-screen flex flex-col">
      <div className="p-6 border-b border-gray-700">
        <Link href="/" className="text-xl font-bold text-bioaf-400">
          bioAF
        </Link>
        <p className="text-xs text-gray-400 mt-1">Computational Biology Platform</p>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => {
          if (item.adminOnly && !isAdmin) return null;
          if ((item as Record<string, unknown>).compBioOnly && !canSeePipelines) return null;
          return (
            <NavItem
              key={item.href}
              label={item.label}
              href={item.href}
              active={item.active}
              isCurrentPage={item.href === "/" ? pathname === "/" : pathname.startsWith(item.href)}
            />
          );
        })}
      </nav>

      <div className="p-4 border-t border-gray-700 text-xs text-gray-500">
        v0.1.0
      </div>
    </aside>
  );
}
