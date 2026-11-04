import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  getMonitoringAlerts,
  getMonitoringScenarios,
  runMonitoringDemo,
  clearMonitoringDemo,
} from "./mockApi.js";

// The mock adds artificial latency; run timers instantly.
async function settle(promise) {
  await vi.runAllTimersAsync();
  return promise;
}

describe("mock safety monitoring (mirrors backend /monitoring/*)", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(async () => {
    await settle(clearMonitoringDemo());
    vi.useRealTimers();
  });

  it("lists the same scenarios as the backend, default first", async () => {
    const ids = (await settle(getMonitoringScenarios())).map((s) => s.id);
    expect(ids[0]).toBe("kitchen_fall");
    expect(ids).toContain("night_wandering");
  });

  it("stacks scenarios per patient and replaces a rerun instead of duplicating", async () => {
    const fall = await settle(runMonitoringDemo({ scenario: "bathroom_fall", patientId: "p1" }));
    const tap = await settle(runMonitoringDemo({ scenario: "tap_running", patientId: "p1" }));
    await settle(runMonitoringDemo({ scenario: "bathroom_fall", patientId: "p1" }));
    await settle(runMonitoringDemo({ scenario: "tap_running", patientId: "p2" }));

    const p1 = await settle(getMonitoringAlerts({ patient_id: "p1" }));
    expect(p1).toHaveLength(fall.length + tap.length);
    expect(p1.every((a) => a.source === "demo" && a.patient_id === "p1")).toBe(true);
  });

  it("rejects an unknown scenario", async () => {
    const run = runMonitoringDemo({ scenario: "nope" });
    const assertion = expect(run).rejects.toThrow(/Unknown scenario/);
    await vi.runAllTimersAsync();
    await assertion;
  });
});
