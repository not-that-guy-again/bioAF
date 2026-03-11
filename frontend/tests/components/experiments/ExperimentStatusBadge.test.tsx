import { render, screen } from "@testing-library/react";
import { ExperimentStatusBadge } from "@/components/experiments/ExperimentStatusBadge";

describe("ExperimentStatusBadge", () => {
  const cases: Array<[string, string]> = [
    ["registered", "Registered"],
    ["library_prep", "Library Prep"],
    ["sequencing", "Sequencing"],
    ["fastq_uploaded", "FASTQ Uploaded"],
    ["processing", "Processing"],
    ["pipeline_complete", "Pipeline Complete"],
    ["reviewed", "Reviewed"],
    ["analysis", "Analysis"],
    ["complete", "Complete"],
  ];

  it.each(cases)("renders label for status %s", (status, expectedLabel) => {
    render(<ExperimentStatusBadge status={status as never} />);
    expect(screen.getByText(expectedLabel)).toBeInTheDocument();
  });

  it("pipeline_complete renders with teal styling", () => {
    render(<ExperimentStatusBadge status="pipeline_complete" />);
    expect(screen.getByText("Pipeline Complete")).toHaveClass("bg-teal-100", "text-teal-800");
  });

  it("complete renders with green styling", () => {
    render(<ExperimentStatusBadge status="complete" />);
    expect(screen.getByText("Complete")).toHaveClass("bg-green-100", "text-green-800");
  });

  it("registered renders with gray styling", () => {
    render(<ExperimentStatusBadge status="registered" />);
    expect(screen.getByText("Registered")).toHaveClass("bg-gray-100", "text-gray-800");
  });
});
