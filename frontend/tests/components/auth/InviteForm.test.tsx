import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { InviteForm } from "@/components/auth/InviteForm";

const mockApiPost = jest.fn();
jest.mock("@/lib/api", () => ({
  api: { post: (...args: unknown[]) => mockApiPost(...args) },
}));

describe("InviteForm", () => {
  beforeEach(() => {
    mockApiPost.mockReset();
  });

  it("renders email input, role selector, and invite button", () => {
    render(<InviteForm />);
    expect(screen.getByPlaceholderText("Email address")).toBeInTheDocument();
    expect(screen.getByRole("combobox")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Invite" })).toBeInTheDocument();
  });

  it("renders all four role options", () => {
    render(<InviteForm />);
    const select = screen.getByRole("combobox");
    expect(select).toContainHTML("Admin");
    expect(select).toContainHTML("Comp Bio");
    expect(select).toContainHTML("Bench");
    expect(select).toContainHTML("Viewer");
  });

  it("calls POST /api/users with email and selected role on invite", async () => {
    mockApiPost.mockResolvedValue({});
    render(<InviteForm />);

    fireEvent.change(screen.getByPlaceholderText("Email address"), {
      target: { value: "alice@bioaf.org" },
    });
    fireEvent.change(screen.getByRole("combobox"), {
      target: { value: "bench" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Invite" }));

    await waitFor(() => {
      expect(mockApiPost).toHaveBeenCalledWith("/api/users", {
        email: "alice@bioaf.org",
        role: "bench",
      });
    });
  });

  it("shows invited email in results list after successful invite", async () => {
    mockApiPost.mockResolvedValue({});
    render(<InviteForm />);

    fireEvent.change(screen.getByPlaceholderText("Email address"), {
      target: { value: "alice@bioaf.org" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Invite" }));

    await waitFor(() => {
      expect(screen.getByText(/alice@bioaf.org/)).toBeInTheDocument();
      expect(screen.getByText(/invited/)).toBeInTheDocument();
    });
  });

  it("shows error message on invite failure", async () => {
    mockApiPost.mockRejectedValue(new Error("User already exists"));
    render(<InviteForm />);

    fireEvent.change(screen.getByPlaceholderText("Email address"), {
      target: { value: "exists@bioaf.org" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Invite" }));

    await waitFor(() => {
      expect(screen.getByText("User already exists")).toBeInTheDocument();
    });
  });

  it("calls bulk invite endpoint with parsed emails", async () => {
    mockApiPost.mockResolvedValue({ results: [{ email: "a@b.com", status: "invited" }] });
    render(<InviteForm />);

    fireEvent.change(screen.getByLabelText(/Bulk invite/i), {
      target: { value: "a@b.com\nb@c.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Bulk Invite" }));

    await waitFor(() => {
      expect(mockApiPost).toHaveBeenCalledWith(
        "/api/users/bulk-invite",
        expect.objectContaining({
          invites: expect.arrayContaining([
            { email: "a@b.com", role: "comp_bio" },
            { email: "b@c.com", role: "comp_bio" },
          ]),
        })
      );
    });
  });
});
