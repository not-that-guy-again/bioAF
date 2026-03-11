import { render, screen, waitFor } from "@testing-library/react";
import { ComponentCatalog } from "@/components/components/ComponentCatalog";
import type { ComponentState } from "@/lib/types";

const mockApiGet = jest.fn();
const mockApiPost = jest.fn();
jest.mock("@/lib/api", () => ({
  api: {
    get: (...args: unknown[]) => mockApiGet(...args),
    post: (...args: unknown[]) => mockApiPost(...args),
  },
  ApiError: class ApiError extends Error {},
}));

jest.mock("next/link", () => ({
  __esModule: true,
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

const components: ComponentState[] = [
  {
    key: "k8s_pipeline_pool",
    name: "K8s Pipeline Pool",
    description: "Kubernetes node pool for pipelines",
    category: "compute",
    enabled: true,
    status: "healthy",
    config: {},
    dependencies: [],
    estimated_monthly_cost: "$100/month",
    updated_at: null,
  },
  {
    key: "slurm_cluster",
    name: "SLURM Cluster",
    description: "Traditional HPC cluster",
    category: "compute",
    enabled: false,
    status: "not_enabled",
    config: {},
    dependencies: [],
    estimated_monthly_cost: "$250/month",
    updated_at: null,
  },
  {
    key: "cellxgene",
    name: "Cellxgene",
    description: "Interactive cell browser",
    category: "visualization",
    enabled: false,
    status: "not_enabled",
    config: {},
    dependencies: [],
    estimated_monthly_cost: "$20/month",
    updated_at: null,
  },
];

describe("ComponentCatalog", () => {
  beforeEach(() => {
    mockApiGet.mockReset();
    // Default to kubernetes stack
    mockApiGet.mockResolvedValue({ compute_stack: "kubernetes" });
  });

  it("renders categories as section headings", async () => {
    render(<ComponentCatalog components={components} onRefresh={jest.fn()} />);
    await waitFor(() => {
      expect(screen.getByText("compute")).toBeInTheDocument();
      expect(screen.getByText("visualization")).toBeInTheDocument();
    });
  });

  it("renders all component cards", async () => {
    render(<ComponentCatalog components={components} onRefresh={jest.fn()} />);
    await waitFor(() => {
      expect(screen.getByText("K8s Pipeline Pool")).toBeInTheDocument();
      expect(screen.getByText("SLURM Cluster")).toBeInTheDocument();
      expect(screen.getByText("Cellxgene")).toBeInTheDocument();
    });
  });

  it("marks SLURM-only components as Coming Soon when stack is kubernetes", async () => {
    render(<ComponentCatalog components={components} onRefresh={jest.fn()} />);
    await waitFor(() => {
      // slurm_cluster is in SLURM_ONLY_COMPONENTS — should show Coming Soon on kubernetes stack
      expect(screen.getByText("Coming Soon")).toBeInTheDocument();
      expect(
        screen.getByText("Coming Soon — available with SLURM compute stack")
      ).toBeInTheDocument();
    });
  });

  it("does not mark Cellxgene as Coming Soon (it is not stack-specific)", async () => {
    render(<ComponentCatalog components={components} onRefresh={jest.fn()} />);
    await waitFor(() => {
      // Cellxgene should have an Enable button, not Coming Soon
      const enableButtons = screen.getAllByRole("button", { name: "Enable" });
      // At least one Enable button for Cellxgene
      expect(enableButtons.length).toBeGreaterThan(0);
    });
  });

  it("marks K8s-only components as Coming Soon when stack is slurm", async () => {
    mockApiGet.mockResolvedValue({ compute_stack: "slurm" });
    render(<ComponentCatalog components={components} onRefresh={jest.fn()} />);
    await waitFor(() => {
      // k8s_pipeline_pool is in K8S_COMPONENTS — should show Coming Soon on slurm stack
      expect(
        screen.getByText("Coming Soon — available with Kubernetes compute stack")
      ).toBeInTheDocument();
    });
  });

  it("fetches compute stack from /api/v1/infrastructure/compute/stack", async () => {
    render(<ComponentCatalog components={components} onRefresh={jest.fn()} />);
    await waitFor(() => {
      expect(mockApiGet).toHaveBeenCalledWith("/api/v1/infrastructure/compute/stack");
    });
  });

  it("defaults to kubernetes if compute stack fetch fails", async () => {
    mockApiGet.mockRejectedValue(new Error("Network error"));
    render(<ComponentCatalog components={components} onRefresh={jest.fn()} />);
    await waitFor(() => {
      // SLURM cluster should still be marked Coming Soon (kubernetes default)
      expect(screen.getByText("Coming Soon")).toBeInTheDocument();
    });
  });
});
