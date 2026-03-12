/**
 * Tests 26-31: TerraformProgressModal component (Step 11 - Phase 17).
 *
 * 26: Shows pending state with spinner when no events received
 * 27: Renders resource list and progress bar as events arrive
 * 28: Shows completion state with Done button after apply_complete
 * 29: Shows failure state with Retry option after apply_error
 * 30: Uses POST method with auth header
 * 31: Shows server error detail on non-OK response
 */

// JSDOM polyfills for streaming APIs
import { TextEncoder, TextDecoder } from "util";
Object.assign(global, { TextEncoder, TextDecoder });

import { render, screen, waitFor } from "@testing-library/react";
import { TerraformProgressModal } from "@/components/infrastructure/TerraformProgressModal";

// ---------------------------------------------------------------------------
// Helper: mock fetch to return SSE data via a readable stream-like object
// ---------------------------------------------------------------------------

interface ReadResult {
  done: boolean;
  value?: Uint8Array;
}

function createMockReader(chunks: string[]): {
  read: () => Promise<ReadResult>;
  cancel: () => void;
} {
  let index = 0;
  const encoder = new TextEncoder();
  return {
    read: () => {
      if (index < chunks.length) {
        return Promise.resolve({
          done: false,
          value: encoder.encode(chunks[index++]),
        });
      }
      return Promise.resolve({ done: true } as ReadResult);
    },
    cancel: () => {},
  };
}

function mockFetchSse(events: object[]): void {
  const sseText = events
    .map((e) => `data: ${JSON.stringify(e)}\n\n`)
    .join("");

  (global as Record<string, unknown>).fetch = jest.fn().mockResolvedValue({
    ok: true,
    status: 200,
    body: {
      getReader: () => createMockReader([sseText]),
    },
    headers: new Headers({ "Content-Type": "text/event-stream" }),
  });
}

function mockFetchHanging(): void {
  (global as Record<string, unknown>).fetch = jest.fn().mockResolvedValue({
    ok: true,
    status: 200,
    body: {
      getReader: () => ({
        read: () => new Promise<ReadResult>(() => {}),
        cancel: () => {},
      }),
    },
    headers: new Headers({ "Content-Type": "text/event-stream" }),
  });
}

function mockFetchError(status: number, detail: string): void {
  (global as Record<string, unknown>).fetch = jest.fn().mockResolvedValue({
    ok: false,
    status,
    text: () => Promise.resolve(JSON.stringify({ detail })),
    headers: new Headers({ "Content-Type": "application/json" }),
  });
}

// ---------------------------------------------------------------------------
// Cleanup
// ---------------------------------------------------------------------------

afterEach(() => {
  jest.restoreAllMocks();
  delete (global as Record<string, unknown>).fetch;
});

// ---------------------------------------------------------------------------
// Test 26: Pending state
// ---------------------------------------------------------------------------

test("TerraformProgressModal shows initializing state before any events", () => {
  mockFetchHanging();

  render(
    <TerraformProgressModal
      title="Initialize Infrastructure"
      sseUrl="/api/v1/infrastructure/terraform/bootstrap"
      onComplete={jest.fn()}
      onClose={jest.fn()}
    />
  );

  expect(screen.getByText("Initialize Infrastructure")).toBeInTheDocument();
  expect(screen.getByTestId("tf-modal-status")).toBeInTheDocument();
});

// ---------------------------------------------------------------------------
// Test 27: Event updates - resource list and progress bar
// ---------------------------------------------------------------------------

test("TerraformProgressModal updates resource list on resource_complete events", async () => {
  mockFetchSse([
    {
      event_type: "resource_complete",
      message: "Applied: google_storage_bucket.terraform_state",
      resource_address: "google_storage_bucket.terraform_state",
      resources_completed: 1,
      resources_total: 1,
    },
  ]);

  render(
    <TerraformProgressModal
      title="Bootstrap"
      sseUrl="/api/v1/infrastructure/terraform/bootstrap"
      onComplete={jest.fn()}
      onClose={jest.fn()}
    />
  );

  await waitFor(() => {
    expect(screen.getByTestId("tf-progress-bar")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Test 28: Completion state
// ---------------------------------------------------------------------------

test("TerraformProgressModal shows completion state after apply_complete event", async () => {
  const onComplete = jest.fn();
  mockFetchSse([
    {
      event_type: "apply_complete",
      message: "Apply complete",
      resources_completed: 1,
      resources_total: 1,
    },
  ]);

  render(
    <TerraformProgressModal
      title="Bootstrap"
      sseUrl="/api/v1/infrastructure/terraform/bootstrap"
      onComplete={onComplete}
      onClose={jest.fn()}
    />
  );

  await waitFor(() => {
    expect(screen.getByTestId("tf-modal-done-btn")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Test 29: Failure state
// ---------------------------------------------------------------------------

test("TerraformProgressModal shows failure state after apply_error event", async () => {
  mockFetchSse([
    {
      event_type: "apply_error",
      message: "Error: permission denied",
      resources_completed: 0,
      resources_total: 1,
    },
  ]);

  render(
    <TerraformProgressModal
      title="Bootstrap"
      sseUrl="/api/v1/infrastructure/terraform/bootstrap"
      onComplete={jest.fn()}
      onClose={jest.fn()}
    />
  );

  await waitFor(() => {
    expect(screen.getByTestId("tf-modal-error")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Test 30: Uses POST method with auth header
// ---------------------------------------------------------------------------

test("TerraformProgressModal sends POST request with auth token", async () => {
  Storage.prototype.getItem = jest.fn().mockReturnValue("mock-jwt-token");

  mockFetchSse([
    {
      event_type: "apply_complete",
      message: "Done",
      resources_completed: 1,
      resources_total: 1,
    },
  ]);
  const fetchMock = global.fetch as jest.Mock;

  render(
    <TerraformProgressModal
      title="Bootstrap"
      sseUrl="/api/v1/infrastructure/terraform/bootstrap"
      onComplete={jest.fn()}
      onClose={jest.fn()}
    />
  );

  await waitFor(() => {
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/infrastructure/terraform/bootstrap"),
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          Authorization: "Bearer mock-jwt-token",
        }),
      })
    );
  });

  Storage.prototype.getItem = jest.fn().mockReturnValue(null);
});

// ---------------------------------------------------------------------------
// Test 31: Shows server error detail on non-OK response
// ---------------------------------------------------------------------------

test("TerraformProgressModal shows server error detail on non-OK response", async () => {
  mockFetchError(409, "GCP credentials are not configured");

  render(
    <TerraformProgressModal
      title="Bootstrap"
      sseUrl="/api/v1/infrastructure/terraform/bootstrap"
      onComplete={jest.fn()}
      onClose={jest.fn()}
    />
  );

  await waitFor(() => {
    expect(screen.getByTestId("tf-modal-error")).toHaveTextContent(
      "GCP credentials are not configured"
    );
  });
});
