export interface User {
  id: number;
  email: string;
  name: string | null;
  role: "admin" | "comp_bio" | "bench" | "viewer";
  status: "active" | "invited" | "deactivated";
  organization_id: number;
  created_at: string;
  updated_at: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface BootstrapStatus {
  setup_complete: boolean;
}

export interface ComponentState {
  key: string;
  name: string;
  description: string;
  category: string;
  enabled: boolean;
  status: string;
  config: Record<string, unknown>;
  dependencies: string[];
  estimated_monthly_cost: string;
  updated_at: string | null;
}

export interface TerraformRun {
  id: number;
  triggered_by_user_id: number;
  action: string;
  component_key: string | null;
  plan_summary: {
    add: Array<{ type: string; name: string; address: string }>;
    change: Array<{ type: string; name: string; address: string }>;
    destroy: Array<{ type: string; name: string; address: string }>;
    add_count: number;
    change_count: number;
    destroy_count: number;
  } | null;
  status: string;
  started_at: string;
  completed_at: string | null;
  error_message: string | null;
}

export interface HealthStatus {
  status: "healthy" | "degraded" | "unhealthy";
  services: Record<string, { status: string; error?: string }>;
}

export interface NavItem {
  label: string;
  href: string;
  icon: string;
  active: boolean;
  phase?: string;
  adminOnly?: boolean;
}
