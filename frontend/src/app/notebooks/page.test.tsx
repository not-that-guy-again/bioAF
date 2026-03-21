import { render, screen, waitFor } from "@testing-library/react";
import NotebooksPage from "./page";

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
  usePathname: () => "/notebooks",
}));

jest.mock("next/link", () => {
  return function MockLink({
    children,
    href,
  }: {
    children: React.ReactNode;
    href: string;
  }) {
    return <a href={href}>{children}</a>;
  };
});

jest.mock("@/lib/api", () => ({
  api: {
    get: jest.fn(),
    post: jest.fn(),
  },
}));

jest.mock("@/lib/auth", () => ({
  getToken: () => "fake-token",
  removeToken: jest.fn(),
  getCurrentUser: () => ({ role: "admin", email: "admin@test.com" }),
  isAuthenticated: () => true,
}));

import { api } from "@/lib/api";

const mockGet = api.get as jest.Mock;

beforeEach(() => {
  mockGet.mockReset();
});

function setupMocks(buildStatus: {
  build_id: string | null;
  build_status: string | null;
  image_uri: string | null;
}) {
  mockGet.mockImplementation((url: string) => {
    if (url.includes("sessions")) return Promise.resolve({ sessions: [] });
    if (url.includes("experiments")) return Promise.resolve({ experiments: [] });
    if (url.includes("build-status")) return Promise.resolve(buildStatus);
    return Promise.resolve({});
  });
}

describe("NotebooksPage build status", () => {
  test("shows building banner when image build is in progress", async () => {
    setupMocks({
      build_id: "abc-123",
      build_status: "WORKING",
      image_uri: null,
    });

    render(<NotebooksPage />);

    await waitFor(() => {
      expect(screen.getByText("Notebook image is building")).toBeInTheDocument();
    });
    expect(screen.getByText(/abc-123/)).toBeInTheDocument();
  });

  test("shows failure banner when last build failed", async () => {
    setupMocks({
      build_id: "fail-456",
      build_status: "FAILURE",
      image_uri: null,
    });

    render(<NotebooksPage />);

    await waitFor(() => {
      expect(screen.getByText("Notebook image build failed")).toBeInTheDocument();
    });
  });

  test("shows no banner when build succeeded", async () => {
    setupMocks({
      build_id: "ok-789",
      build_status: "SUCCESS",
      image_uri: "us-central1-docker.pkg.dev/proj/bioaf-images/bioaf-scrna:latest",
    });

    render(<NotebooksPage />);

    await waitFor(() => {
      expect(screen.getByText("Launch New Session")).toBeInTheDocument();
    });
    expect(screen.queryByText("Notebook image is building")).not.toBeInTheDocument();
    expect(screen.queryByText("Notebook image build failed")).not.toBeInTheDocument();
  });

  test("shows no banner when no build exists", async () => {
    setupMocks({
      build_id: null,
      build_status: null,
      image_uri: null,
    });

    render(<NotebooksPage />);

    await waitFor(() => {
      expect(screen.getByText("Launch New Session")).toBeInTheDocument();
    });
    expect(screen.queryByText("Notebook image is building")).not.toBeInTheDocument();
    expect(screen.queryByText("Notebook image build failed")).not.toBeInTheDocument();
  });
});
