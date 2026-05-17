import { render } from "@testing-library/react";
import axe from "axe-core";
import { describe, expect, test } from "vitest";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorBoundary } from "@/components/ui/ErrorBoundary";

function ThrowError(): never {
  throw new Error("test error");
}

describe("a11y — UI primitives", () => {
  test("EmptyState has no violations", async () => {
    const { container } = render(
      <EmptyState
        icon="📁"
        title="No projects yet"
        description="Create your first project to start tracking tasks."
        action={<button type="button">Create project</button>}
      />,
    );
    const results = await axe.run(container);
    expect(results.violations).toHaveLength(0);
  });

  test("ErrorBoundary fallback UI has no violations", async () => {
    const { container } = render(
      <ErrorBoundary>
        <ThrowError />
      </ErrorBoundary>,
    );
    const results = await axe.run(container);
    expect(results.violations).toHaveLength(0);
  });
});
