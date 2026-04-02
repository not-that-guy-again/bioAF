import { render, screen, fireEvent } from "@testing-library/react";
import { Sidebar } from "./Sidebar";

jest.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
}));

jest.mock("next/link", () => {
  return function MockLink({
    children,
    href,
  }: {
    children: React.ReactNode;
    href: string;
  }) {
    return <a href={href}>{children}</a>;
  };
});

jest.mock("@/lib/auth", () => ({
  getCurrentUser: () => ({ role_name: "admin", email: "admin@test.com" }),
}));

jest.mock("@/hooks/usePermissions", () => ({
  usePermissions: () => ({
    canAccess: () => true,
    roleName: "admin",
    loading: false,
  }),
}));

const mockComponents = jest.fn();
jest.mock("@/hooks/useComponents", () => ({
  useComponents: () => mockComponents(),
}));

beforeEach(() => {
  mockComponents.mockReset();
});

function makeComponent(key: string, category: string, enabled: boolean) {
  return { key, name: key, description: "", category, enabled, status: enabled ? "ready" : "disabled", config: {}, dependencies: [], estimated_monthly_cost: "", updated_at: null };
}

describe("Sidebar component gating", () => {
  test("hides Pipelines section when no pipeline_orchestration component is enabled", () => {
    mockComponents.mockReturnValue({
      components: [
        makeComponent("nextflow_k8s", "pipeline_orchestration", false),
        makeComponent("snakemake_k8s", "pipeline_orchestration", false),
        makeComponent("jupyter_k8s", "analysis", true),
      ],
      loading: false,
      refetch: jest.fn(),
    });

    render(<Sidebar />);

    expect(screen.queryByText("Pipelines")).not.toBeInTheDocument();
  });

  test("shows Pipelines section when a pipeline_orchestration component is enabled", () => {
    mockComponents.mockReturnValue({
      components: [
        makeComponent("nextflow_k8s", "pipeline_orchestration", true),
        makeComponent("jupyter_k8s", "analysis", true),
      ],
      loading: false,
      refetch: jest.fn(),
    });

    render(<Sidebar />);

    expect(screen.getByText("Pipelines")).toBeInTheDocument();
  });

  test("hides Notebooks child when neither jupyter_k8s nor rstudio_k8s is enabled", () => {
    mockComponents.mockReturnValue({
      components: [
        makeComponent("jupyter_k8s", "analysis", false),
        makeComponent("rstudio_k8s", "analysis", false),
      ],
      loading: false,
      refetch: jest.fn(),
    });

    render(<Sidebar />);

    // Expand Workbench to check children
    fireEvent.click(screen.getByText("Workbench"));

    expect(screen.queryByText("Notebooks")).not.toBeInTheDocument();
  });

  test("shows Notebooks child when jupyter_k8s is enabled", () => {
    mockComponents.mockReturnValue({
      components: [
        makeComponent("jupyter_k8s", "analysis", true),
        makeComponent("rstudio_k8s", "analysis", false),
      ],
      loading: false,
      refetch: jest.fn(),
    });

    render(<Sidebar />);

    fireEvent.click(screen.getByText("Workbench"));

    expect(screen.getByText("Notebooks")).toBeInTheDocument();
  });

  test("shows Notebooks child when rstudio_k8s is enabled", () => {
    mockComponents.mockReturnValue({
      components: [
        makeComponent("jupyter_k8s", "analysis", false),
        makeComponent("rstudio_k8s", "analysis", true),
      ],
      loading: false,
      refetch: jest.fn(),
    });

    render(<Sidebar />);

    fireEvent.click(screen.getByText("Workbench"));

    expect(screen.getByText("Notebooks")).toBeInTheDocument();
  });

  test("shows all sections when components are still loading", () => {
    mockComponents.mockReturnValue({
      components: [],
      loading: true,
      refetch: jest.fn(),
    });

    render(<Sidebar />);

    // While loading, sections should still appear (no false negatives)
    expect(screen.getByText("Pipelines")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Workbench"));
    expect(screen.getByText("Notebooks")).toBeInTheDocument();
  });
});
