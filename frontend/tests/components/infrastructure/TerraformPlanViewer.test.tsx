import { render, screen, fireEvent } from "@testing-library/react";
import { TerraformPlanViewer } from "@/components/components/TerraformPlanViewer";
import type { TerraformRun } from "@/lib/types";

const mockPlanSummary: TerraformRun["plan_summary"] = {
  add: [
    { type: "google_container_node_pool", name: "bioaf-pipelines", address: "google_container_node_pool.pipelines" },
    { type: "google_storage_bucket", name: "bioaf-ingest", address: "google_storage_bucket.ingest" },
  ],
  change: [
    { type: "google_container_cluster", name: "bioaf", address: "google_container_cluster.bioaf" },
  ],
  destroy: [
    { type: "google_filestore_instance", name: "bioaf-nfs", address: "google_filestore_instance.nfs" },
  ],
  add_count: 2,
  change_count: 1,
  destroy_count: 1,
};

describe("TerraformPlanViewer", () => {
  it("renders no plan message when planSummary is null", () => {
    render(<TerraformPlanViewer planSummary={null} onApply={jest.fn()} onCancel={jest.fn()} />);
    expect(screen.getByText("No plan available")).toBeInTheDocument();
  });

  it("renders add, change, destroy counts", () => {
    render(
      <TerraformPlanViewer planSummary={mockPlanSummary} onApply={jest.fn()} onCancel={jest.fn()} />
    );
    expect(screen.getByText("+2")).toBeInTheDocument();
    expect(screen.getByText("~1")).toBeInTheDocument();
    expect(screen.getByText("-1")).toBeInTheDocument();
  });

  it("lists resources to create", () => {
    render(
      <TerraformPlanViewer planSummary={mockPlanSummary} onApply={jest.fn()} onCancel={jest.fn()} />
    );
    expect(screen.getByText("Resources to create:")).toBeInTheDocument();
    expect(screen.getByText(/google_container_node_pool\.bioaf-pipelines/)).toBeInTheDocument();
    expect(screen.getByText(/google_storage_bucket\.bioaf-ingest/)).toBeInTheDocument();
  });

  it("lists resources to modify", () => {
    render(
      <TerraformPlanViewer planSummary={mockPlanSummary} onApply={jest.fn()} onCancel={jest.fn()} />
    );
    expect(screen.getByText("Resources to modify:")).toBeInTheDocument();
    expect(screen.getByText(/google_container_cluster\.bioaf/)).toBeInTheDocument();
  });

  it("lists resources to destroy", () => {
    render(
      <TerraformPlanViewer planSummary={mockPlanSummary} onApply={jest.fn()} onCancel={jest.fn()} />
    );
    expect(screen.getByText("Resources to destroy:")).toBeInTheDocument();
    expect(screen.getByText(/google_filestore_instance\.bioaf-nfs/)).toBeInTheDocument();
  });

  it("calls onApply when Apply Changes is clicked", () => {
    const onApply = jest.fn();
    render(
      <TerraformPlanViewer planSummary={mockPlanSummary} onApply={onApply} onCancel={jest.fn()} />
    );
    fireEvent.click(screen.getByRole("button", { name: "Apply Changes" }));
    expect(onApply).toHaveBeenCalled();
  });

  it("calls onCancel when Cancel is clicked", () => {
    const onCancel = jest.fn();
    render(
      <TerraformPlanViewer planSummary={mockPlanSummary} onApply={jest.fn()} onCancel={onCancel} />
    );
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onCancel).toHaveBeenCalled();
  });

  it("does not render Resources to create section when add list is empty", () => {
    const summaryNoAdds = { ...mockPlanSummary, add: [], add_count: 0 };
    render(
      <TerraformPlanViewer planSummary={summaryNoAdds} onApply={jest.fn()} onCancel={jest.fn()} />
    );
    expect(screen.queryByText("Resources to create:")).not.toBeInTheDocument();
  });
});
