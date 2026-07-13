import { describe, expect, it } from "vitest";

import { APP_NAME, FRONTEND_STACK } from "../lib/project";

describe("frontend scaffold", () => {
  it("defines the application name", () => {
    expect(APP_NAME).toBe("Binance Market Data Operations Console");
  });

  it("includes the required frontend stack", () => {
    expect(FRONTEND_STACK).toContain("Next.js App Router");
    expect(FRONTEND_STACK).toContain("TypeScript");
    expect(FRONTEND_STACK).toContain("Tailwind CSS");
    expect(FRONTEND_STACK).toContain("TanStack Query");
    expect(FRONTEND_STACK).toContain("Zustand");
    expect(FRONTEND_STACK).toContain("Vitest");
  });
});
