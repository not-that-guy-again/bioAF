import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import GcpSettingsPage from "@/app/settings/gcp/page";

const mockPush = jest.fn();
jest.mock("next/navigation", () => ({
  usePathname: () => "/settings/gcp",
  useRouter: () => ({ push: mockPush }),
}));

jest.mock("@/lib/auth", () => ({
  isAuthenticated: () => true,
  getCurrentUser: () => ({ email: "admin@bioaf.org", role: "admin", sub: "1" }),
}));

const mockApiGet = jest.fn();
const mockApiPut = jest.fn();
const mockApiPost = jest.fn();

jest.mock("@/lib/api", () => ({
  api: {
    get: (...args: unknown[]) => mockApiGet(...args),
    put: (...args: unknown[]) => mockApiPut(...args),
    post: (...args: unknown[]) => mockApiPost(...args),
  },
}));

const defaultConfig = {
  gcp_project_id: "my-project-123",
  gcp_region: "us-central1",
  gcp_zone: "us-central1-a",
  org_slug: "my-bioaf-org",
  gcp_credentials_configured: false,
  gcp_validation_status: null,
  gcp_credential_source: "vm_default",
};

describe("GCP Settings Page", () => {
  beforeEach(() => {
    mockApiGet.mockReset();
    mockApiPut.mockReset();
    mockApiPost.mockReset();
    mockApiGet.mockResolvedValue(defaultConfig);
    mockApiPut.mockResolvedValue(defaultConfig);
  });

  // Test 18: Page renders with heading
  it("renders GCP Configuration heading", async () => {
    render(<GcpSettingsPage />);
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "GCP Configuration" })).toBeInTheDocument();
    });
  });

  // Test 19: Page loads existing config from API
  it("loads existing config values from the API", async () => {
    render(<GcpSettingsPage />);
    await waitFor(() => {
      const projectInput = screen.getByTestId("gcp-project-id-input");
      expect((projectInput as HTMLInputElement).value).toBe("my-project-123");
    });
    expect(mockApiGet).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/settings/gcp"),
    );
  });

  // Test 20: Org slug validation shows error for invalid input
  it("shows validation error for invalid org slug", async () => {
    render(<GcpSettingsPage />);
    await waitFor(() => screen.getByTestId("org-slug-input"));

    const slugInput = screen.getByTestId("org-slug-input");
    fireEvent.change(slugInput, { target: { value: "-bad-slug-" } });

    const saveBtn = screen.getByTestId("save-gcp-config-btn");
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(screen.getByTestId("org-slug-error")).toBeInTheDocument();
    });
  });

  // Test 21: Save button calls PUT API
  it("save button calls PUT /api/v1/settings/gcp", async () => {
    render(<GcpSettingsPage />);
    await waitFor(() => screen.getByTestId("save-gcp-config-btn"));

    fireEvent.click(screen.getByTestId("save-gcp-config-btn"));

    await waitFor(() => {
      expect(mockApiPut).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/settings/gcp"),
        expect.any(Object),
      );
    });
  });

  // Test 22: Validate button calls POST validate API
  it("validate button calls POST /api/v1/settings/gcp/validate", async () => {
    mockApiPost.mockResolvedValue({
      passed: false,
      checks: [
        { name: "credentials_loaded", passed: false, message: "No creds", status: "failed" },
      ],
    });

    render(<GcpSettingsPage />);
    await waitFor(() => screen.getByTestId("validate-gcp-btn"));

    fireEvent.click(screen.getByTestId("validate-gcp-btn"));

    await waitFor(() => {
      expect(mockApiPost).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/settings/gcp/validate"),
      );
    });
  });

  // Test 23: Validation results display after validate
  it("displays validation results after validate is clicked", async () => {
    mockApiPost.mockResolvedValue({
      passed: false,
      checks: [
        { name: "credentials_loaded", passed: false, message: "No credentials found", status: "failed" },
      ],
    });

    render(<GcpSettingsPage />);
    await waitFor(() => screen.getByTestId("validate-gcp-btn"));

    fireEvent.click(screen.getByTestId("validate-gcp-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("validation-results")).toBeInTheDocument();
      expect(screen.getByText(/credentials_loaded/i)).toBeInTheDocument();
    });
  });
});
