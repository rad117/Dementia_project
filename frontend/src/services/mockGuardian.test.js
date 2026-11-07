import { describe, expect, it } from "vitest";
import { addGuardianContact, deleteGuardianContact, getGuardianContacts } from "./mockApi.js";

describe("mock guardian contacts", () => {
  it("adds, lists per patient and removes", async () => {
    const c = await addGuardianContact({ patientId: "P1", name: "Ravi", phone: "+919876543210", channel: "sms" });
    await addGuardianContact({ patientId: "P2", name: "Meena", phone: "+919811111111", channel: "whatsapp" });
    expect((await getGuardianContacts("P1")).map((x) => x.name)).toEqual(["Ravi"]);
    await deleteGuardianContact(c.id);
    expect(await getGuardianContacts("P1")).toEqual([]);
  });

  it("rejects numbers without a country code", async () => {
    await expect(addGuardianContact({ patientId: "P1", name: "X", phone: "98765" })).rejects.toThrow(/international/);
  });
});
