import { describe, expect, it } from "vitest";
import { mockPatients } from "../data/mockPatients.js";
import { addGuardianContact, deleteGuardianContact, getGuardianContacts, sendGuardianTest } from "./mockApi.js";

const [{ id: P1 }, { id: P2 }] = mockPatients;

describe("mock guardian contacts", () => {
  it("adds, lists per patient and removes", async () => {
    const c = await addGuardianContact({ patientId: P1, name: "Ravi", phone: "+919876543210", channel: "sms" });
    await addGuardianContact({ patientId: P2, name: "Meena", phone: "+919811111111", channel: "whatsapp" });
    expect((await getGuardianContacts(P1)).map((x) => x.name)).toEqual(["Ravi"]);
    await deleteGuardianContact(c.id);
    expect(await getGuardianContacts(P1)).toEqual([]);
  });

  it("rejects numbers without a country code", async () => {
    await expect(addGuardianContact({ patientId: P1, name: "X", phone: "98765" })).rejects.toThrow(/international/);
  });

  it("matches the real API's not-found errors", async () => {
    await expect(addGuardianContact({ patientId: "NOPE", name: "X", phone: "+919876543210" })).rejects.toThrow(/Patient not found/);
    await expect(deleteGuardianContact(99999)).rejects.toThrow(/Contact not found/);
    await expect(sendGuardianTest(99999)).rejects.toThrow(/Contact not found/);
  });
});
