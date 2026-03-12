import { render, screen, waitFor } from "@testing-library/react";

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

jest.mock("@/lib/auth", () => ({
  isAuthenticated: () => true,
}));

const mockApiGet = jest.fn();
const mockApiPut = jest.fn();
jest.mock("@/lib/api", () => ({
  api: {
    get: (...args: unknown[]) => mockApiGet(...args),
    put: (...args: unknown[]) => mockApiPut(...args),
  },
}));

jest.mock("@/components/layout/Sidebar", () => ({
  Sidebar: () => <div data-testid="sidebar">Sidebar</div>,
}));
jest.mock("@/components/layout/Header", () => ({
  Header: () => <div data-testid="header">Header</div>,
}));

import NotebookSettingsPage from "@/app/settings/notebooks/page";

describe("NotebookSettingsPage", () => {
  beforeEach(() => {
    mockApiGet.mockReset();
    mockApiPut.mockReset();
  });

  // Test 37: Settings page renders idle timeout and image URI fields
  it("renders idle timeout and image URI fields", async () => {
    mockApiGet.mockResolvedValue({
      idle_timeout_hours: 4,
      idle_warning_minutes: 15,
      max_sessions_per_user: 2,
      bioaf_scrna_image: "us-central1-docker.pkg.dev/proj/repo/bioaf-scrna:latest",
    });

    render(<NotebookSettingsPage />);
    await waitFor(() => {
      expect(screen.getByLabelText(/idle timeout/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/image/i)).toBeInTheDocument();
    });
  });
});
