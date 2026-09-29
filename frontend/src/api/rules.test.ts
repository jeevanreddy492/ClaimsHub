import { describe, expect, it } from "vitest";
import { allowedClaimMoves, label, money, sharesTotal } from "./rules";

describe("allowedClaimMoves", () => {
  it("lets a supervisor approve or deny a claim in review", () => {
    expect(allowedClaimMoves("IN_REVIEW", "SUPERVISOR")).toEqual(["APPROVED", "DENIED"]);
  });
  it("hides approve/deny from an adjuster", () => {
    expect(allowedClaimMoves("IN_REVIEW", "ADJUSTER")).toEqual([]);
    expect(allowedClaimMoves("RECEIVED", "ADJUSTER")).toEqual(["IN_REVIEW"]);
  });
  it("gives a viewer no actions", () => {
    expect(allowedClaimMoves("RECEIVED", "VIEWER")).toEqual([]);
  });
});

describe("helpers", () => {
  it("adds shares without float errors", () => {
    expect(sharesTotal(["33.33", "33.33", "33.34"])).toBe(100);
    expect(sharesTotal(["50", ""])).toBe(50);
  });
  it("formats money and labels", () => {
    expect(money("1200")).toBe("$1,200.00");
    expect(money(null)).toBe("—");
    expect(label("IN_REVIEW")).toBe("In review");
  });
});
