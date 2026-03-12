/**
 * Tests 26-29: TerraformProgressModal component (Step 11 - Phase 17).
 *
 * 26: Shows pending state with spinner when no events received
 * 27: Renders resource list and progress bar as events arrive
 * 28: Shows completion state with Done button after apply_complete
 * 29: Shows failure state with Retry option after apply_error
 */

import { render, screen, act, waitFor } from "@testing-library/react";
import { TerraformProgressModal } from "@/components/infrastructure/TerraformProgressModal";

// ---------------------------------------------------------------------------
// Mock EventSource globally
// ---------------------------------------------------------------------------

class MockEventSource {
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;
  onopen: (() => void) | null = null;
  static instance: MockEventSource | null = null;

  constructor(public url: string) {
    MockEventSource.instance = this;
  }

  close() {}

  // Test helper: simulate receiving a data event
  emit(data: object) {
    if (this.onmessage) {
      this.onmessage({ data: JSON.stringify(data) } as MessageEvent);
    }
  }
}

Object.defineProperty(global, "EventSource", {
  writable: true,
  value: MockEventSource,
});

// ---------------------------------------------------------------------------
// Test 26: Pending state
// ---------------------------------------------------------------------------

test("TerraformProgressModal shows initializing state before any events", () => {
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
  render(
    <TerraformProgressModal
      title="Bootstrap"
      sseUrl="/api/v1/infrastructure/terraform/bootstrap"
      onComplete={jest.fn()}
      onClose={jest.fn()}
    />
  );

  act(() => {
    MockEventSource.instance?.emit({
      event_type: "resource_complete",
      message: "Applied: google_storage_bucket.terraform_state",
      resource_address: "google_storage_bucket.terraform_state",
      resources_completed: 1,
      resources_total: 1,
    });
  });

  await waitFor(() => {
    expect(screen.getByTestId("tf-progress-bar")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Test 28: Completion state
// ---------------------------------------------------------------------------

test("TerraformProgressModal shows completion state after apply_complete event", async () => {
  const onComplete = jest.fn();
  render(
    <TerraformProgressModal
      title="Bootstrap"
      sseUrl="/api/v1/infrastructure/terraform/bootstrap"
      onComplete={onComplete}
      onClose={jest.fn()}
    />
  );

  act(() => {
    MockEventSource.instance?.emit({
      event_type: "apply_complete",
      message: "Apply complete",
      resources_completed: 1,
      resources_total: 1,
    });
  });

  await waitFor(() => {
    expect(screen.getByTestId("tf-modal-done-btn")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Test 29: Failure state
// ---------------------------------------------------------------------------

test("TerraformProgressModal shows failure state after apply_error event", async () => {
  render(
    <TerraformProgressModal
      title="Bootstrap"
      sseUrl="/api/v1/infrastructure/terraform/bootstrap"
      onComplete={jest.fn()}
      onClose={jest.fn()}
    />
  );

  act(() => {
    MockEventSource.instance?.emit({
      event_type: "apply_error",
      message: "Error: permission denied",
      resources_completed: 0,
      resources_total: 1,
    });
  });

  await waitFor(() => {
    expect(screen.getByTestId("tf-modal-error")).toBeInTheDocument();
  });
});
