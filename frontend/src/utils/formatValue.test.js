import { describe, expect, it } from "vitest";
import { formatValue } from "./formatValue.js";

describe("formatValue", () => {
  it("rounds raw floats to at most two decimals", () => {
    expect(formatValue(235.62711174009996)).toBe("235.63");
    expect(formatValue(0.19200000000000003)).toBe("0.19");
  });

  it("leaves integers, strings and missing values alone", () => {
    expect(formatValue(3)).toBe("3");
    expect(formatValue("7 / 15")).toBe("7 / 15");
    expect(formatValue(null)).toBe(null);
    expect(formatValue(undefined)).toBe(undefined);
  });
});
