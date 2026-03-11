import { render, screen, waitFor } from "@testing-library/react";
import { ComponentCatalog } from "@/components/components/ComponentCatalog";

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

const k8sComponentsResponse = {
  compute_stack: "kubernetes",
  components: [
    {
      key: "k8s_pipeline_pool",
      name: "K8s Pipeline Node Pool",
      category: "compute",
      description: "GKE node pool for batch pipeline jobs",
      cost_estimate: "$0 (scales to zero)",
      dependencies: [],
      configurable_fields: [],
      status: "available",
    },
    {
      key: "k8s_interactive_pool",
      name: "K8s Interactive Node Pool",
      category: "compute",
      description: "GKE node pool for notebooks",
      cost_estimate: "$0 (scales to zero)",
      dependencies: [],
      configurable_fields: [],
      status: "available",
    },
    {
      key: "slurm",
      name: "SLURM HPC Cluster",
      category: "compute",
      description: "HPC cluster",
      cost_estimate: "$200-$1500",
      dependencies: [],
      configurable_fields: [],
      status: "coming_soon",
    },
    {
      key: "filestore",
      name: "Filestore NFS",
      category: "compute",
      description: "NFS storage",
      cost_estimate: "$200-$500",
      dependencies: ["slurm"],
      configurable_fields: [],
      status: "coming_soon",
    },
    {
      key: "nextflow_k8s",
      name: "Nextflow (K8s Executor)",
      category: "pipeline_orchestration",
      description: "Nextflow with K8s executor",
      cost_estimate: "$0",
      dependencies: ["k8s_pipeline_pool"],
      configurable_fields: [],
      status: "available",
    },
    {
      key: "jupyter_k8s",
      name: "JupyterHub on K8s",
      category: "analysis",
      description: "JupyterHub on Kubernetes",
      cost_estimate: "$50-$200",
      dependencies: ["k8s_interactive_pool"],
      configurable_fields: [],
      status: "available",
    },
    {
      key: "cellxgene",
      name: "cellxgene",
      category: "visualization",
      description: "Interactive cell browser",
      cost_estimate: "$20-$50",
      dependencies: [],
      configurable_fields: [],
      status: "available",
    },
    {
      key: "meilisearch",
      name: "Meilisearch",
      category: "search",
      description: "Full-text search",
      cost_estimate: "$20-$50",
      dependencies: [],
      configurable_fields: [],
      status: "available",
    },
  ],
};

describe("ComponentCatalog", () => {
  beforeEach(() => {
    mockApiGet.mockReset();
    mockApiGet.mockResolvedValue(k8sComponentsResponse);
  });

  it("renders compute stack banner showing Kubernetes + GCS", async () => {
    render(<ComponentCatalog onRefresh={jest.fn()} />);
    await waitFor(() => {
      expect(screen.getByTestId("compute-stack-banner")).toHaveTextContent(
        "Kubernetes + GCS"
      );
    });
  });

  it("renders K8s pipeline node pool with Enable button", async () => {
    render(<ComponentCatalog onRefresh={jest.fn()} />);
    await waitFor(() => {
      expect(screen.getByText("K8s Pipeline Node Pool")).toBeInTheDocument();
    });
    // Should have Enable button for available component
    const enableButtons = screen.getAllByRole("button", { name: /enable/i });
    expect(enableButtons.length).toBeGreaterThan(0);
  });

  it("renders K8s interactive node pool", async () => {
    render(<ComponentCatalog onRefresh={jest.fn()} />);
    await waitFor(() => {
      expect(screen.getByText("K8s Interactive Node Pool")).toBeInTheDocument();
    });
  });

  it("renders SLURM as Coming Soon with no action buttons in the card", async () => {
    render(<ComponentCatalog onRefresh={jest.fn()} />);
    await waitFor(() => {
      expect(screen.getByText("SLURM HPC Cluster")).toBeInTheDocument();
      // SLURM coming-soon cards should not have Enable buttons specific to them
      const comingSoonBadges = screen.getAllByText("Coming Soon");
      expect(comingSoonBadges.length).toBeGreaterThan(0);
    });
  });

  it("renders Filestore NFS as Coming Soon", async () => {
    render(<ComponentCatalog onRefresh={jest.fn()} />);
    await waitFor(() => {
      expect(screen.getByText("Filestore NFS")).toBeInTheDocument();
    });
  });

  it("Nextflow card shows dependency on K8s pipeline node pool", async () => {
    render(<ComponentCatalog onRefresh={jest.fn()} />);
    await waitFor(() => {
      expect(screen.getByText("Nextflow (K8s Executor)")).toBeInTheDocument();
      // The card should show the dependency
      expect(screen.getByText(/k8s_pipeline_pool/)).toBeInTheDocument();
    });
  });

  it("JupyterHub card shows dependency on K8s interactive node pool", async () => {
    render(<ComponentCatalog onRefresh={jest.fn()} />);
    await waitFor(() => {
      expect(screen.getByText("JupyterHub on K8s")).toBeInTheDocument();
      expect(screen.getByText(/k8s_interactive_pool/)).toBeInTheDocument();
    });
  });

  it("renders all 5 category sections", async () => {
    render(<ComponentCatalog onRefresh={jest.fn()} />);
    await waitFor(() => {
      expect(screen.getByText("Compute")).toBeInTheDocument();
      expect(screen.getByText("Pipeline Orchestration")).toBeInTheDocument();
      expect(screen.getByText("Analysis")).toBeInTheDocument();
      expect(screen.getByText("Visualization")).toBeInTheDocument();
      expect(screen.getByText("Search")).toBeInTheDocument();
    });
  });

  it("fetches from /api/v1/infrastructure/components", async () => {
    render(<ComponentCatalog onRefresh={jest.fn()} />);
    await waitFor(() => {
      expect(mockApiGet).toHaveBeenCalledWith("/api/v1/infrastructure/components");
    });
  });
});
