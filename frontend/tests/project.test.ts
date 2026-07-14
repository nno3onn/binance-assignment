import { describe, expect, it } from "vitest";

import { APP_NAME, FRONTEND_STACK } from "../lib/project";

describe("frontend scaffold", () => {
  it("defines the application name", () => {
    expect(APP_NAME).toBe("시장 데이터 운영 대시보드");
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
