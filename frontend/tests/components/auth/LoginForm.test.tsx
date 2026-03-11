import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { LoginForm } from "@/components/auth/LoginForm";

describe("LoginForm", () => {
  it("renders email and password fields with submit button", () => {
    render(<LoginForm onSubmit={jest.fn()} />);
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign In" })).toBeInTheDocument();
  });

  it("calls onSubmit with email and password on form submit", async () => {
    const onSubmit = jest.fn().mockResolvedValue(undefined);
    render(<LoginForm onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "test@bioaf.org" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "secret123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith("test@bioaf.org", "secret123");
    });
  });

  it("shows Signing in... and disables button while submitting", async () => {
    let resolve: () => void;
    const onSubmit = jest.fn(
      () => new Promise<void>((res) => { resolve = res; })
    );
    render(<LoginForm onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "test@bioaf.org" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "pass" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Signing in..." })).toBeDisabled();
    });

    resolve!();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Sign In" })).not.toBeDisabled();
    });
  });

  it("displays error message when error prop is provided", () => {
    render(<LoginForm onSubmit={jest.fn()} error="Invalid credentials" />);
    expect(screen.getByText("Invalid credentials")).toBeInTheDocument();
  });

  it("does not display error section when no error prop", () => {
    render(<LoginForm onSubmit={jest.fn()} />);
    expect(screen.queryByText("Invalid credentials")).not.toBeInTheDocument();
  });
});
