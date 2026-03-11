import { render, screen, fireEvent } from "@testing-library/react";
import SnapshotComparisonTable from "@/components/SnapshotComparisonTable";
import type { AnalysisSnapshot } from "@/lib/types";

const makeSnapshot = (overrides: Partial<AnalysisSnapshot> = {}): AnalysisSnapshot => ({
  id: 1,
  experiment_id: 10,
  project_id: null,
  notebook_session_id: 5,
  user_id: 1,
  user_name: "Dr. Sarah",
  label: "QC filtering",
  notes: null,
  object_type: "anndata",
  cell_count: 5000,
  gene_count: 20000,
  cluster_count: 12,
  starred: false,
  figure_url: null,
  created_at: "2026-03-10T12:00:00Z",
  ...overrides,
});

const snapshots = [
  makeSnapshot({ id: 1, label: "QC filtering", cell_count: 5000, user_name: "Sarah" }),
  makeSnapshot({ id: 2, label: "Clustering", cell_count: 4800, user_name: "Alex", object_type: "seurat" }),
  makeSnapshot({ id: 3, label: "Trajectory", cell_count: 4500, user_name: "Maria", starred: true }),
];

describe("SnapshotComparisonTable", () => {
  it("renders all snapshot labels", () => {
    render(<SnapshotComparisonTable snapshots={snapshots} onCompare={jest.fn()} />);
    expect(screen.getByText("QC filtering")).toBeInTheDocument();
    expect(screen.getByText("Clustering")).toBeInTheDocument();
    expect(screen.getByText("Trajectory")).toBeInTheDocument();
  });

  it("renders AnnData badge for anndata snapshots", () => {
    render(<SnapshotComparisonTable snapshots={snapshots} onCompare={jest.fn()} />);
    const badges = screen.getAllByText("AnnData");
    expect(badges.length).toBeGreaterThan(0);
  });

  it("renders Seurat badge for seurat snapshots", () => {
    render(<SnapshotComparisonTable snapshots={snapshots} onCompare={jest.fn()} />);
    expect(screen.getByText("Seurat")).toBeInTheDocument();
  });

  it("renders star icon for starred snapshots", () => {
    render(<SnapshotComparisonTable snapshots={snapshots} onCompare={jest.fn()} />);
    // Starred snapshot has ★ (★)
    expect(screen.getByText("★")).toBeInTheDocument();
  });

  it("does not show Compare Selected button when fewer than 2 selected", () => {
    render(<SnapshotComparisonTable snapshots={snapshots} onCompare={jest.fn()} />);
    expect(screen.queryByText(/Compare Selected/)).not.toBeInTheDocument();

    const checkboxes = screen.getAllByRole("checkbox");
    fireEvent.click(checkboxes[0]);
    expect(screen.queryByText(/Compare Selected/)).not.toBeInTheDocument();
  });

  it("shows Compare Selected button when 2+ checkboxes selected", () => {
    render(<SnapshotComparisonTable snapshots={snapshots} onCompare={jest.fn()} />);
    const checkboxes = screen.getAllByRole("checkbox");
    fireEvent.click(checkboxes[0]);
    fireEvent.click(checkboxes[1]);
    expect(screen.getByText(/Compare Selected \(2\)/)).toBeInTheDocument();
  });

  it("calls onCompare with selected IDs when Compare Selected clicked", () => {
    const onCompare = jest.fn();
    render(<SnapshotComparisonTable snapshots={snapshots} onCompare={onCompare} />);
    const checkboxes = screen.getAllByRole("checkbox");
    fireEvent.click(checkboxes[0]);
    fireEvent.click(checkboxes[1]);
    fireEvent.click(screen.getByText(/Compare Selected/));
    expect(onCompare).toHaveBeenCalledWith(expect.arrayContaining([1, 2]));
  });

  it("Clear button deselects all snapshots", () => {
    render(<SnapshotComparisonTable snapshots={snapshots} onCompare={jest.fn()} />);
    const checkboxes = screen.getAllByRole("checkbox");
    fireEvent.click(checkboxes[0]);
    fireEvent.click(checkboxes[1]);
    expect(screen.getByText(/Compare Selected/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Clear" }));
    expect(screen.queryByText(/Compare Selected/)).not.toBeInTheDocument();
  });

  it("limits selection to 5 snapshots", () => {
    const manySnaps = Array.from({ length: 6 }, (_, i) =>
      makeSnapshot({ id: i + 1, label: `Snap ${i + 1}` })
    );
    render(<SnapshotComparisonTable snapshots={manySnaps} onCompare={jest.fn()} />);
    const checkboxes = screen.getAllByRole("checkbox");
    checkboxes.forEach((cb) => fireEvent.click(cb));
    // Should show (5) not (6)
    expect(screen.getByText(/Compare Selected \(5\)/)).toBeInTheDocument();
  });

  it("sorts by label when Label header is clicked", () => {
    render(<SnapshotComparisonTable snapshots={snapshots} onCompare={jest.fn()} />);
    fireEvent.click(screen.getByText(/Label/));

    const rows = screen.getAllByRole("row").slice(1); // skip header
    const labels = rows.map((r) => r.textContent);
    const labelTexts = rows.map((r) => r.querySelector("td:nth-child(3)")?.textContent ?? "");
    // After ascending sort by label: Clustering, QC filtering, Trajectory
    expect(labelTexts[0]).toContain("Clustering");
  });

  it("toggles sort direction on second click of same column", () => {
    render(<SnapshotComparisonTable snapshots={snapshots} onCompare={jest.fn()} />);
    fireEvent.click(screen.getByText(/Label/)); // asc
    fireEvent.click(screen.getByText(/Label/)); // desc

    const rows = screen.getAllByRole("row").slice(1);
    const labelTexts = rows.map((r) => r.querySelector("td:nth-child(3)")?.textContent ?? "");
    // Descending: Trajectory, QC filtering, Clustering
    expect(labelTexts[0]).toContain("Trajectory");
  });
});
