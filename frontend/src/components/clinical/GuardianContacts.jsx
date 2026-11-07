import { useEffect, useState } from "react";
import { addGuardianContact, deleteGuardianContact, getGuardianContacts, sendGuardianTest } from "../../services/index.js";
import Button from "../common/Button.jsx";
import styles from "./GuardianContacts.module.css";

const CHANNEL_LABEL = { sms: "SMS", whatsapp: "WhatsApp" };

// Family members who receive a text when a serious live safety alert is raised
// for this patient. Simulated (demo) alerts never message anyone.
export default function GuardianContacts({ patientId }) {
  const [contacts, setContacts] = useState(null);
  const [form, setForm] = useState({ name: "", phone: "", channel: "sms" });
  const [note, setNote] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getGuardianContacts(patientId)
      .then((c) => !cancelled && setContacts(c))
      .catch((e) => !cancelled && (setContacts([]), setNote({ error: true, text: e.message })));
    return () => {
      cancelled = true;
    };
  }, [patientId]);

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  async function handleAdd(e) {
    e.preventDefault();
    setBusy(true);
    setNote(null);
    try {
      const created = await addGuardianContact({ patientId, ...form, name: form.name.trim(), phone: form.phone.trim() });
      setContacts((c) => [...(c ?? []), created]);
      setForm({ name: "", phone: "", channel: form.channel });
    } catch (err) {
      setNote({ error: true, text: err.message });
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(id) {
    try {
      await deleteGuardianContact(id);
      setContacts((c) => c.filter((x) => x.id !== id));
    } catch (err) {
      setNote({ error: true, text: err.message });
    }
  }

  async function handleTest(id) {
    setNote(null);
    try {
      const r = await sendGuardianTest(id);
      const text =
        r.status === "sent" ? "Test message sent." :
        r.status === "dry_run" ? "Messaging is not configured on the server, so nothing was sent." :
        `Test message failed${r.detail ? `: ${r.detail}` : "."}`;
      setNote({ error: r.status === "failed", text });
    } catch (err) {
      setNote({ error: true, text: err.message });
    }
  }

  return (
    <div>
      {contacts && contacts.length === 0 && (
        <p className={styles.meta}>No family contacts yet. Add someone to be texted when a serious alert is raised.</p>
      )}
      {contacts && contacts.length > 0 && (
        <ul className={styles.list}>
          {contacts.map((c) => (
            <li key={c.id} className={styles.row}>
              <span className={styles.who}>{c.name}</span>
              <span className={styles.meta}>{c.phone} · {CHANNEL_LABEL[c.channel] ?? c.channel}</span>
              <span className={styles.actions}>
                <Button variant="secondary" size="sm" type="button" onClick={() => handleTest(c.id)}>Send test</Button>
                <Button variant="secondary" size="sm" type="button" onClick={() => handleDelete(c.id)}>Remove</Button>
              </span>
            </li>
          ))}
        </ul>
      )}

      <form className={styles.form} onSubmit={handleAdd}>
        <label className={styles.field}>Name
          <input value={form.name} onChange={set("name")} required maxLength={100} />
        </label>
        <label className={styles.field}>Phone (with country code)
          <input value={form.phone} onChange={set("phone")} required placeholder="+919876543210" inputMode="tel" />
        </label>
        <label className={styles.field}>Channel
          <select value={form.channel} onChange={set("channel")}>
            <option value="sms">SMS</option>
            <option value="whatsapp">WhatsApp</option>
          </select>
        </label>
        <Button type="submit" size="sm" disabled={busy}>Add contact</Button>
      </form>
      {note && <p className={`${styles.msg} ${note.error ? styles.err : ""}`} role="status">{note.text}</p>}
    </div>
  );
}
