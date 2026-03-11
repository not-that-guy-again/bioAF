import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { StorageSection } from "@/components/components/StorageSection";

const mockApiGet = jest.fn();
jest.mock("@/lib/api", () => ({
  api: {
    get: (...args: unknown[]) => mockApiGet(...args),
  },
}));

jest.mock("next/link", () => ({
  __esModule: true,
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

// Mock clipboard
Object.assign(navigator, {
  clipboard: {
    writeText: jest.fn().mockResolvedValue(undefined),
  },
});

const bucketsResponse = {
  org_slug: "test-org",
  buckets: [
    {
      name: "bioaf-ingest-test-org",
      purpose: "Landing zone for incoming sequencing files.",
      is_ingest: true,
      size_gb: 0.0,
      object_count: 0,
    },
    {
      name: "bioaf-raw-test-org",
      purpose: "Permanent storage for raw sequencing data.",
      is_ingest: false,
      size_gb: 2.5,
      object_count: 45,
    },
    {
      name: "bioaf-working-test-org",
      purpose: "Intermediate pipeline outputs.",
      is_ingest: false,
      size_gb: 1.2,
      object_count: 120,
    },
    {
      name: "bioaf-results-test-org",
      purpose: "Final pipeline results.",
      is_ingest: false,
      size_gb: 0.8,
      object_count: 35,
    },
    {
      name: "bioaf-config-backups-test-org",
      purpose: "Automated backups of platform configuration.",
      is_ingest: false,
      size_gb: 0.01,
      object_count: 5,
    },
  ],
};

describe("StorageSection", () => {
  beforeEach(() => {
    mockApiGet.mockReset();
    mockApiGet.mockResolvedValue(bucketsResponse);
  });

  it("renders 5 bucket cards", async () => {
    render(<StorageSection />);
    await waitFor(() => {
      expect(screen.getByText("bioaf-ingest-test-org")).toBeInTheDocument();
      expect(screen.getByText("bioaf-raw-test-org")).toBeInTheDocument();
      expect(screen.getByText("bioaf-working-test-org")).toBeInTheDocument();
      expect(screen.getByText("bioaf-results-test-org")).toBeInTheDocument();
      expect(screen.getByText("bioaf-config-backups-test-org")).toBeInTheDocument();
    });
  });

  it("ingest bucket card has distinct styling", async () => {
    render(<StorageSection />);
    await waitFor(() => {
      const ingestCard = screen.getByTestId("bucket-card-bioaf-ingest-test-org");
      expect(ingestCard.className).toMatch(/border-teal|border-blue|ring-teal|ring-blue/);
    });
  });

  it("ingest bucket guidance panel contains gsutil command", async () => {
    render(<StorageSection />);
    await waitFor(() => {
      expect(
        screen.getByText(/gsutil cp .* gs:\/\/bioaf-ingest-test-org\//),
      ).toBeInTheDocument();
    });
  });

  it("copy button copies gs:// URI to clipboard", async () => {
    render(<StorageSection />);
    await waitFor(() => {
      expect(screen.getAllByRole("button", { name: /copy/i }).length).toBeGreaterThan(0);
    });
    const copyButtons = screen.getAllByRole("button", { name: /copy/i });
    fireEvent.click(copyButtons[0]);
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      expect.stringMatching(/^gs:\/\//)
    );
  });

  it("link to naming profiles navigates to /settings/naming-profiles", async () => {
    render(<StorageSection />);
    await waitFor(() => {
      const namingLink = screen.getByText(/naming profiles/i).closest("a");
      expect(namingLink).toHaveAttribute("href", "/settings/naming-profiles");
    });
  });

  it("link to dataset browser navigates to /data/browser", async () => {
    render(<StorageSection />);
    await waitFor(() => {
      const dataLink = screen.getByText(/view ingested files/i).closest("a");
      expect(dataLink).toHaveAttribute("href", "/data/browser");
    });
  });

  it("fetches from /api/v1/infrastructure/storage/buckets", async () => {
    render(<StorageSection />);
    await waitFor(() => {
      expect(mockApiGet).toHaveBeenCalledWith("/api/v1/infrastructure/storage/buckets");
    });
  });
});
