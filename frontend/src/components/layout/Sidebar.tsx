"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NavItem } from "./NavItem";
import { getCurrentUser } from "@/lib/auth";

const navItems = [
  { label: "Home", href: "/", icon: "home", active: true },
  { label: "Experiments", href: "/experiments", icon: "flask", active: false, phase: "Phase 2" },
  { label: "Data", href: "/data", icon: "database", active: false, phase: "Phase 2" },
  { label: "Compute", href: "/compute", icon: "server", active: false, phase: "Phase 3" },
  { label: "Results", href: "/results", icon: "chart", active: false, phase: "Phase 5" },
  { label: "Components", href: "/components", icon: "puzzle", active: true },
  { label: "Users & Roles", href: "/admin/users", icon: "users", active: true, adminOnly: true },
  { label: "Settings", href: "/admin/settings", icon: "settings", active: true, adminOnly: true },
];

export function Sidebar() {
  const pathname = usePathname();
  const user = getCurrentUser();
  const isAdmin = user?.role === "admin";

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
          return (
            <NavItem
              key={item.href}
              label={item.label}
              href={item.href}
              active={item.active}
              phase={item.phase}
              isCurrentPage={pathname === item.href}
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
