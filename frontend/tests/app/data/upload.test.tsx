import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import DataUploadPage from "@/app/data/upload/page";

jest.mock("@/components/layout/Sidebar", () => ({
  Sidebar: () => <div data-testid="sidebar" />,
}));
jest.mock("@/components/layout/Header", () => ({
  Header: () => <div data-testid="header" />,
}));
jest.mock("@/lib/auth", () => ({
  getToken: () => "test-token",
  removeToken: jest.fn(),
}));

const mockUpload = jest.fn();
jest.mock("@/lib/api", () => ({
  api: {
    upload: (...args: unknown[]) => mockUpload(...args),
  },
}));

beforeEach(() => {
  mockUpload.mockReset();
  mockUpload.mockResolvedValue({ id: 1, filename: "sample.fastq.gz" });
});

describe("DataUploadPage", () => {
  it("calls /api/files/upload/simple when uploading a file", async () => {
    render(<DataUploadPage />);

    const file = new File(["data"], "sample.fastq.gz", { type: "application/gzip" });
    const input = document.querySelector("input[type='file']") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => screen.getByText("Upload All"));
    fireEvent.click(screen.getByText("Upload All"));

    await waitFor(() => expect(mockUpload).toHaveBeenCalledTimes(1));
    const [calledPath] = mockUpload.mock.calls[0];
    expect(calledPath).toContain("/api/files/upload/simple");
    expect(calledPath).not.toContain("/api/files/upload?");
    expect(calledPath).not.toBe("/api/files/upload");
  });

  it("appends experiment_id query param when provided", async () => {
    render(<DataUploadPage />);

    fireEvent.change(screen.getByPlaceholderText("Experiment ID"), {
      target: { value: "42" },
    });

    const file = new File(["data"], "sample.fastq.gz", { type: "application/gzip" });
    const input = document.querySelector("input[type='file']") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => screen.getByText("Upload All"));
    fireEvent.click(screen.getByText("Upload All"));

    await waitFor(() => expect(mockUpload).toHaveBeenCalledTimes(1));
    const [calledPath] = mockUpload.mock.calls[0];
    expect(calledPath).toContain("/api/files/upload/simple");
    expect(calledPath).toContain("experiment_id=42");
  });
});
