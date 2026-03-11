/**
 * Tests for route redirects defined in next.config.js.
 * These verify the redirect configuration is correct by importing and checking the config.
 */

// eslint-disable-next-line @typescript-eslint/no-var-requires
const nextConfig = require("../next.config.js");

interface Redirect {
  source: string;
  destination: string;
  permanent: boolean;
}

describe("Route Redirects", () => {
  let redirects: Redirect[];

  beforeAll(async () => {
    redirects = await nextConfig.redirects();
  });

  it("redirects /home to /dashboard", () => {
    const redirect = redirects.find((r: Redirect) => r.source === "/home");
    expect(redirect).toBeDefined();
    expect(redirect!.destination).toBe("/dashboard");
  });

  it("redirects /compute/pipelines/catalog to /pipelines/catalog", () => {
    const redirect = redirects.find(
      (r: Redirect) => r.source === "/compute/pipelines/catalog",
    );
    expect(redirect).toBeDefined();
    expect(redirect!.destination).toBe("/pipelines/catalog");
  });

  it("redirects /admin/users to /settings/users", () => {
    const redirect = redirects.find(
      (r: Redirect) => r.source === "/admin/users",
    );
    expect(redirect).toBeDefined();
    expect(redirect!.destination).toBe("/settings/users");
  });

  it("redirects /components to /infrastructure/components", () => {
    const redirect = redirects.find(
      (r: Redirect) => r.source === "/components",
    );
    expect(redirect).toBeDefined();
    expect(redirect!.destination).toBe("/infrastructure/components");
  });

  it("redirects /admin/settings to /settings/info", () => {
    const redirect = redirects.find(
      (r: Redirect) => r.source === "/admin/settings",
    );
    expect(redirect).toBeDefined();
    expect(redirect!.destination).toBe("/settings/info");
  });

  it("contains all expected redirect sources", () => {
    const sources = redirects.map((r: Redirect) => r.source);
    expect(sources).toContain("/home");
    expect(sources).toContain("/compute");
    expect(sources).toContain("/admin/costs");
    expect(sources).toContain("/admin/backups");
    expect(sources).toContain("/admin/access-logs");
    expect(sources).toContain("/references");
    expect(sources).toContain("/environments");
    expect(sources).toContain("/packages");
  });
});
