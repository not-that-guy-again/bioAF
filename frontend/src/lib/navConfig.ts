export interface NavChild {
  label: string;
  path: string;
}

export interface NavSection {
  label: string;
  path?: string;
  icon: string;
  children?: NavChild[];
  adminOnly?: boolean;
}

export const navConfig: NavSection[] = [
  { label: "Dashboard", path: "/dashboard", icon: "home" },
  {
    label: "Results",
    icon: "chart",
    children: [
      { label: "QC Dashboards", path: "/results/qc-dashboards" },
      { label: "Cellxgene", path: "/results/cellxgene" },
      { label: "Plot Archive", path: "/results/plot-archive" },
    ],
  },
  {
    label: "Pipelines",
    icon: "play",
    children: [
      { label: "Pipeline Catalog", path: "/pipelines/catalog" },
      { label: "Pipeline Runs", path: "/pipelines/runs" },
      { label: "Pipeline Scheduling", path: "/pipelines/scheduling" },
    ],
  },
  { label: "Projects", path: "/projects", icon: "folder" },
  {
    label: "Experiments",
    icon: "flask",
    children: [
      { label: "Experiment Templates", path: "/experiments/templates" },
      { label: "Experiment List", path: "/experiments" },
    ],
  },
  { label: "Notebooks", path: "/notebooks", icon: "notebook" },
  {
    label: "Data & Files",
    icon: "database",
    children: [
      { label: "Upload", path: "/data/upload" },
      { label: "Dataset Browser", path: "/data/browser" },
      { label: "Documents", path: "/data/documents" },
      { label: "Reference Data", path: "/data/references" },
    ],
  },
  {
    label: "Infrastructure",
    icon: "server",
    children: [
      { label: "Components", path: "/infrastructure/components" },
      { label: "Compute", path: "/infrastructure/compute" },
      { label: "Environments", path: "/infrastructure/environments" },
      { label: "Packages", path: "/infrastructure/packages" },
      { label: "Cost Center", path: "/infrastructure/cost-center" },
      { label: "Backup & Recovery", path: "/infrastructure/backup" },
    ],
  },
  {
    label: "Settings",
    icon: "settings",
    adminOnly: true,
    children: [
      { label: "Users & Roles", path: "/settings/users" },
      { label: "Access Logs", path: "/settings/access-logs" },
      { label: "Naming Profiles", path: "/settings/naming-profiles" },
      { label: "SMTP Configuration", path: "/settings/smtp" },
      { label: "Slack Integration", path: "/settings/slack" },
      { label: "Information", path: "/settings/info" },
    ],
  },
];

/**
 * Find the nav section and child for a given pathname.
 * Returns { section, child } or { section } for top-level pages.
 */
export function findNavMatch(
  pathname: string,
): { section: NavSection; child?: NavChild } | null {
  for (const section of navConfig) {
    if (section.path && pathname === section.path) {
      return { section };
    }
    if (section.children) {
      for (const child of section.children) {
        if (pathname === child.path || pathname.startsWith(child.path + "/")) {
          return { section, child };
        }
      }
    }
  }
  // Special case: root path maps to dashboard
  if (pathname === "/") {
    return { section: navConfig[0] };
  }
  return null;
}
