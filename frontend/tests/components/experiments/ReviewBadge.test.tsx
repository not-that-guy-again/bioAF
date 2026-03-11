import { render, screen } from "@testing-library/react";
import { ReviewBadge } from "@/components/experiments/ReviewBadge";

describe("ReviewBadge", () => {
  it("renders Approved with green styling", () => {
    render(<ReviewBadge verdict="approved" />);
    const badge = screen.getByText("Approved");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass("bg-green-100", "text-green-800");
  });

  it("renders Approved w/ Caveats with yellow styling", () => {
    render(<ReviewBadge verdict="approved_with_caveats" />);
    const badge = screen.getByText("Approved w/ Caveats");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass("bg-yellow-100", "text-yellow-800");
  });

  it("renders Rejected with red styling", () => {
    render(<ReviewBadge verdict="rejected" />);
    const badge = screen.getByText("Rejected");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass("bg-red-100", "text-red-800");
  });

  it("renders Revision Requested with orange styling", () => {
    render(<ReviewBadge verdict="revision_requested" />);
    const badge = screen.getByText("Revision Requested");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass("bg-orange-100", "text-orange-800");
  });

  it("applies larger text and padding for size=md", () => {
    render(<ReviewBadge verdict="approved" size="md" />);
    const badge = screen.getByText("Approved");
    expect(badge).toHaveClass("px-3", "py-1", "text-sm");
  });

  it("applies smaller text and padding for size=sm (default)", () => {
    render(<ReviewBadge verdict="approved" />);
    const badge = screen.getByText("Approved");
    expect(badge).toHaveClass("px-2", "py-0.5", "text-xs");
  });
});
