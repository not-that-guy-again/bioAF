import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { SetupWizard } from "@/components/auth/SetupWizard";

const mockApiPost = jest.fn();
jest.mock("@/lib/api", () => ({
  api: { post: (...args: unknown[]) => mockApiPost(...args) },
}));

jest.mock("@/lib/auth", () => ({
  setToken: jest.fn(),
}));

// InviteForm uses api internally; its mock is covered above.

describe("SetupWizard", () => {
  beforeEach(() => {
    mockApiPost.mockReset();
    mockApiPost.mockResolvedValue({ access_token: "tok", email_sent: true });
  });

  it("renders the 7-step indicator on mount", () => {
    render(<SetupWizard onComplete={jest.fn()} />);
    // 7 step circles labeled 1–7
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("7")).toBeInTheDocument();
  });

  it("step 0: shows Create Admin Account form", () => {
    render(<SetupWizard onComplete={jest.fn()} />);
    expect(screen.getByRole("heading", { name: "Create Admin Account" })).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.getByLabelText("Confirm Password")).toBeInTheDocument();
  });

  it("step 0: shows error when passwords do not match", async () => {
    render(<SetupWizard onComplete={jest.fn()} />);

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "admin@bioaf.org" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "abc" } });
    fireEvent.change(screen.getByLabelText("Confirm Password"), { target: { value: "xyz" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Admin Account" }));

    expect(await screen.findByText("Passwords do not match")).toBeInTheDocument();
    expect(mockApiPost).not.toHaveBeenCalled();
  });

  it("step 0: advances to step 1 after successful admin creation", async () => {
    render(<SetupWizard onComplete={jest.fn()} />);

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "admin@bioaf.org" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "pass123" } });
    fireEvent.change(screen.getByLabelText("Confirm Password"), { target: { value: "pass123" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Admin Account" }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Verify Email" })).toBeInTheDocument();
    });
  });

  it("step 4: renders Kubernetes + GCS (recommended) and SLURM + NFS (coming soon) cards", async () => {
    // Navigate to step 4 by mocking each intermediate API call
    render(<SetupWizard onComplete={jest.fn()} />);

    // Step 0 → 1
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "a@b.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "pw" } });
    fireEvent.change(screen.getByLabelText("Confirm Password"), { target: { value: "pw" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Admin Account" }));
    await screen.findByRole("heading", { name: "Verify Email" });

    // Step 1 → 2 (skip)
    fireEvent.click(screen.getByRole("button", { name: "Skip for now" }));
    await screen.findByRole("heading", { name: "Organization Name" });

    // Step 2 → 3
    mockApiPost.mockResolvedValueOnce({});
    fireEvent.change(screen.getByLabelText("Organization Name"), { target: { value: "Acme Bio" } });
    fireEvent.click(screen.getByRole("button", { name: "Save Organization Name" }));
    await screen.findByRole("heading", { name: "SMTP Configuration" });

    // Step 3 → 4 (skip)
    fireEvent.click(screen.getByRole("button", { name: "Skip for now" }));
    await screen.findByRole("heading", { name: "Compute Stack" });

    // Kubernetes card is present and labeled Recommended
    expect(screen.getByTestId("compute-stack-kubernetes")).toBeInTheDocument();
    expect(screen.getByText("Kubernetes + GCS")).toBeInTheDocument();
    expect(screen.getByText("Recommended")).toBeInTheDocument();

    // SLURM card is present and labeled Coming Soon
    expect(screen.getByTestId("compute-stack-slurm")).toBeInTheDocument();
    expect(screen.getByText("SLURM + NFS")).toBeInTheDocument();
    expect(screen.getByText("Coming Soon")).toBeInTheDocument();
  });

  it("step 4: Kubernetes is selected by default and continues with K8s label", async () => {
    render(<SetupWizard onComplete={jest.fn()} />);

    // Navigate to compute stack step
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "a@b.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "pw" } });
    fireEvent.change(screen.getByLabelText("Confirm Password"), { target: { value: "pw" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Admin Account" }));
    await screen.findByRole("heading", { name: "Verify Email" });
    fireEvent.click(screen.getByRole("button", { name: "Skip for now" }));
    await screen.findByRole("heading", { name: "Organization Name" });
    mockApiPost.mockResolvedValueOnce({});
    fireEvent.change(screen.getByLabelText("Organization Name"), { target: { value: "Org" } });
    fireEvent.click(screen.getByRole("button", { name: "Save Organization Name" }));
    await screen.findByRole("heading", { name: "SMTP Configuration" });
    fireEvent.click(screen.getByRole("button", { name: "Skip for now" }));
    await screen.findByRole("heading", { name: "Compute Stack" });

    // Continue button shows Kubernetes label
    expect(screen.getByRole("button", { name: "Continue with Kubernetes + GCS" })).toBeInTheDocument();
  });

  it("step 4: clicking Kubernetes card keeps it selected", async () => {
    render(<SetupWizard onComplete={jest.fn()} />);

    // Fast-navigate to compute stack
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "a@b.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "pw" } });
    fireEvent.change(screen.getByLabelText("Confirm Password"), { target: { value: "pw" } });
    fireEvent.click(screen.getByRole("button", { name: "Create Admin Account" }));
    await screen.findByRole("heading", { name: "Verify Email" });
    fireEvent.click(screen.getByRole("button", { name: "Skip for now" }));
    await screen.findByRole("heading", { name: "Organization Name" });
    mockApiPost.mockResolvedValueOnce({});
    fireEvent.change(screen.getByLabelText("Organization Name"), { target: { value: "Org" } });
    fireEvent.click(screen.getByRole("button", { name: "Save Organization Name" }));
    await screen.findByRole("heading", { name: "SMTP Configuration" });
    fireEvent.click(screen.getByRole("button", { name: "Skip for now" }));
    await screen.findByRole("heading", { name: "Compute Stack" });

    fireEvent.click(screen.getByTestId("compute-stack-kubernetes"));
    expect(screen.getByRole("button", { name: "Continue with Kubernetes + GCS" })).toBeInTheDocument();
  });
});
