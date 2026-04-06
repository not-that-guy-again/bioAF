import { render, screen, fireEvent } from "@testing-library/react";
import { GettingStarted } from "@/components/onboarding/GettingStarted";

// Mock next/navigation
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
}));

// Suppress img loading errors in JSDOM
beforeAll(() => {
  jest.spyOn(console, "error").mockImplementation(() => {});
});
afterAll(() => {
  jest.restoreAllMocks();
});

describe("GettingStarted", () => {
  const onComplete = jest.fn();

  beforeEach(() => {
    onComplete.mockReset();
  });

  it("renders the first slide with correct title", () => {
    render(<GettingStarted onComplete={onComplete} />);
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
  });

  it("has next/prev navigation buttons", () => {
    render(<GettingStarted onComplete={onComplete} />);
    expect(screen.getByLabelText("Next slide")).toBeInTheDocument();
    // Prev should be disabled on first slide
    expect(screen.getByLabelText("Previous slide")).toBeDisabled();
  });

  it("navigates forward and backward with buttons", () => {
    render(<GettingStarted onComplete={onComplete} />);

    fireEvent.click(screen.getByLabelText("Next slide"));
    expect(screen.getByText("Active Projects")).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("Previous slide"));
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
  });

  it("navigates with keyboard arrows", () => {
    render(<GettingStarted onComplete={onComplete} />);

    fireEvent.keyDown(window, { key: "ArrowRight" });
    expect(screen.getByText("Active Projects")).toBeInTheDocument();

    fireEvent.keyDown(window, { key: "ArrowLeft" });
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
  });

  it('"Skip tour" link is always visible', () => {
    render(<GettingStarted onComplete={onComplete} />);
    expect(screen.getByText("Skip tour")).toBeInTheDocument();

    // Navigate to slide 2
    fireEvent.click(screen.getByLabelText("Next slide"));
    expect(screen.getByText("Skip tour")).toBeInTheDocument();
  });

  it("skip tour calls onComplete", () => {
    render(<GettingStarted onComplete={onComplete} />);
    fireEvent.click(screen.getByText("Skip tour"));
    expect(onComplete).toHaveBeenCalledTimes(1);
  });

  it("final slide shows Go to Dashboard button", () => {
    render(<GettingStarted onComplete={onComplete} />);

    // Navigate to last slide (17th = index 16)
    for (let i = 0; i < 16; i++) {
      fireEvent.click(screen.getByLabelText("Next slide"));
    }

    expect(screen.getByText("CellxGene")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /go to dashboard/i })).toBeInTheDocument();
  });

  it("Go to Dashboard calls onComplete", () => {
    render(<GettingStarted onComplete={onComplete} />);

    for (let i = 0; i < 16; i++) {
      fireEvent.click(screen.getByLabelText("Next slide"));
    }

    fireEvent.click(screen.getByRole("button", { name: /go to dashboard/i }));
    expect(onComplete).toHaveBeenCalledTimes(1);
  });

  it('standalone mode shows "Close" instead of "Go to Dashboard"', () => {
    render(<GettingStarted onComplete={onComplete} standalone />);

    for (let i = 0; i < 16; i++) {
      fireEvent.click(screen.getByLabelText("Next slide"));
    }

    expect(screen.queryByText(/go to dashboard/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /close/i })).toBeInTheDocument();
  });

  it("renders 17 dot indicators", () => {
    render(<GettingStarted onComplete={onComplete} />);
    const dots = screen.getAllByTestId("slide-dot");
    expect(dots).toHaveLength(17);
  });
});
