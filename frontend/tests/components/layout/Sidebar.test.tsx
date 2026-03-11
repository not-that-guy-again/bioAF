import { render, screen, fireEvent } from "@testing-library/react";
import { Sidebar } from "@/components/layout/Sidebar";

// Mock next/navigation
const mockPathname = jest.fn().mockReturnValue("/dashboard");
jest.mock("next/navigation", () => ({
  usePathname: () => mockPathname(),
}));

// Mock auth
const mockGetCurrentUser = jest.fn();
jest.mock("@/lib/auth", () => ({
  getCurrentUser: () => mockGetCurrentUser(),
}));

describe("Sidebar", () => {
  beforeEach(() => {
    mockPathname.mockReturnValue("/dashboard");
    mockGetCurrentUser.mockReturnValue({
      email: "test@bioaf.org",
      role: "admin",
      sub: "1",
    });
  });

  it("renders all 9 top-level items for admin user", () => {
    render(<Sidebar />);
    const nav = screen.getByTestId("sidebar-nav");
    // 9 top-level sections: Dashboard, Results, Pipelines, Projects,
    // Experiments, Notebooks, Data & Files, Infrastructure, Settings
    expect(nav).toHaveTextContent("Dashboard");
    expect(nav).toHaveTextContent("Results");
    expect(nav).toHaveTextContent("Pipelines");
    expect(nav).toHaveTextContent("Projects");
    expect(nav).toHaveTextContent("Experiments");
    expect(nav).toHaveTextContent("Notebooks");
    expect(nav).toHaveTextContent("Data & Files");
    expect(nav).toHaveTextContent("Infrastructure");
    expect(nav).toHaveTextContent("Settings");
  });

  it("hides Settings when user role is not admin", () => {
    mockGetCurrentUser.mockReturnValue({
      email: "bench@bioaf.org",
      role: "bench",
      sub: "2",
    });
    render(<Sidebar />);
    const nav = screen.getByTestId("sidebar-nav");
    expect(nav).not.toHaveTextContent("Settings");
  });

  it("shows Settings when user role is admin", () => {
    render(<Sidebar />);
    const nav = screen.getByTestId("sidebar-nav");
    expect(nav).toHaveTextContent("Settings");
  });

  it("navigates to correct path for single-page items", () => {
    render(<Sidebar />);
    const dashboardLink = screen.getByText("Dashboard").closest("a");
    expect(dashboardLink).toHaveAttribute("href", "/dashboard");
    const projectsLink = screen.getByText("Projects").closest("a");
    expect(projectsLink).toHaveAttribute("href", "/projects");
    const notebooksLink = screen.getByText("Notebooks").closest("a");
    expect(notebooksLink).toHaveAttribute("href", "/notebooks");
  });

  it("toggles children visibility when clicking expandable section", () => {
    render(<Sidebar />);
    // Results section should not show children initially (not active)
    expect(screen.queryByText("QC Dashboards")).not.toBeInTheDocument();

    // Click Results to expand
    fireEvent.click(screen.getByText("Results"));
    expect(screen.getByText("QC Dashboards")).toBeInTheDocument();
    expect(screen.getByText("Cellxgene")).toBeInTheDocument();
    expect(screen.getByText("Plot Archive")).toBeInTheDocument();

    // Click again to collapse
    fireEvent.click(screen.getByText("Results"));
    expect(screen.queryByText("QC Dashboards")).not.toBeInTheDocument();
  });

  it("highlights active path for top-level items", () => {
    mockPathname.mockReturnValue("/dashboard");
    render(<Sidebar />);
    const dashboardLink = screen.getByText("Dashboard").closest("a");
    expect(dashboardLink?.className).toContain("bg-bioaf-700");
  });

  it("highlights active path and auto-expands parent for child items", () => {
    mockPathname.mockReturnValue("/pipelines/runs");
    render(<Sidebar />);
    // Parent section should be auto-expanded
    expect(screen.getByText("Pipeline Runs")).toBeInTheDocument();
    // Child item should be highlighted
    const runsLink = screen.getByText("Pipeline Runs").closest("a");
    expect(runsLink?.className).toContain("bg-bioaf-700");
  });

  it("shows child items when parent section is expanded", () => {
    render(<Sidebar />);
    // Expand Infrastructure
    fireEvent.click(screen.getByText("Infrastructure"));
    expect(screen.getByText("Components")).toBeInTheDocument();
    expect(screen.getByText("Compute")).toBeInTheDocument();
    expect(screen.getByText("Environments")).toBeInTheDocument();
    expect(screen.getByText("Packages")).toBeInTheDocument();
    expect(screen.getByText("Cost Center")).toBeInTheDocument();
    expect(screen.getByText("Backup & Recovery")).toBeInTheDocument();
  });
});
