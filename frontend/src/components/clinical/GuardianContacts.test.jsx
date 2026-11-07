import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getGuardianContacts } from "../../services/index.js";
import GuardianContacts from "./GuardianContacts.jsx";

vi.mock("../../services/index.js", () => ({
  getGuardianContacts: vi.fn(),
  addGuardianContact: vi.fn(),
  deleteGuardianContact: vi.fn(),
  sendGuardianTest: vi.fn(),
}));

const ravi = { id: 1, patient_id: "A", name: "Ravi", phone: "+919876543210", channel: "sms" };

describe("GuardianContacts", () => {
  beforeEach(() => vi.clearAllMocks());

  it("hides the previous patient's contacts while the next patient's load", async () => {
    getGuardianContacts.mockResolvedValueOnce([ravi]);
    const { rerender } = render(<GuardianContacts patientId="A" />);
    await screen.findByText("Ravi");

    let finish;
    getGuardianContacts.mockReturnValueOnce(new Promise((resolve) => (finish = resolve)));
    rerender(<GuardianContacts patientId="B" />);

    expect(screen.queryByText("Ravi")).toBeNull();
    expect(screen.queryByRole("button", { name: "Remove" })).toBeNull();
    finish([]);
    await waitFor(() => expect(screen.getByText(/No family contacts yet/)).toBeTruthy());
  });
});
