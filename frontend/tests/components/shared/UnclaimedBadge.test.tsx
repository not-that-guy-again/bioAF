import { render, screen } from "@testing-library/react";
import { UnclaimedBadge } from "@/components/shared/UnclaimedBadge";

describe("UnclaimedBadge", () => {
  it("renders Unclaimed text", () => {
    render(<UnclaimedBadge />);
    expect(screen.getByText("Unclaimed")).toBeInTheDocument();
  });

  it("has yellow background styling", () => {
    render(<UnclaimedBadge />);
    const badge = screen.getByText("Unclaimed").closest("span");
    expect(badge).toHaveClass("bg-yellow-100", "text-yellow-800");
  });

  it("tooltip references generic entity type when no entityType provided", () => {
    render(<UnclaimedBadge />);
    const badge = screen.getByText("Unclaimed").closest("span");
    expect(badge).toHaveAttribute("title", expect.stringContaining("entity"));
  });

  it("tooltip references specific entityType when provided", () => {
    render(<UnclaimedBadge entityType="experiment" />);
    const badge = screen.getByText("Unclaimed").closest("span");
    expect(badge).toHaveAttribute("title", expect.stringContaining("experiment"));
  });
});
