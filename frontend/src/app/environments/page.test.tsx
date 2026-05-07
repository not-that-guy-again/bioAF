import { render, waitFor } from "@testing-library/react";
import EnvironmentsPage from "./page";

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
  usePathname: () => "/environments",
}));

jest.mock("@/lib/api", () => ({
  api: {
    get: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
  },
}));

jest.mock("@/lib/auth", () => ({
  getToken: () => "fake-token",
  removeToken: jest.fn(),
  getCurrentUser: () => ({ role_name: "admin", email: "admin@test.com" }),
  isAuthenticated: () => true,
}));

import { api } from "@/lib/api";

const mockGet = api.get as jest.Mock;

beforeEach(() => {
  mockGet.mockReset();
  mockGet.mockResolvedValue({ environments: [], total: 0 });
});

describe("Workbench EnvironmentsPage filter", () => {
  test("'All' filter excludes pipeline envs (does not call unfiltered list)", async () => {
    render(<EnvironmentsPage />);

    // Initial load should request notebook + work_node, never the bare
    // /api/v1/environments which would include pipeline envs.
    await waitFor(() => {
      expect(mockGet).toHaveBeenCalled();
    });

    expect(mockGet).not.toHaveBeenCalledWith("/api/v1/environments");
    expect(mockGet).toHaveBeenCalledWith(
      expect.stringMatching(/^\/api\/v1\/environments\?type=notebook$/)
    );
    expect(mockGet).toHaveBeenCalledWith(
      expect.stringMatching(/^\/api\/v1\/environments\?type=work_node$/)
    );
  });
});
