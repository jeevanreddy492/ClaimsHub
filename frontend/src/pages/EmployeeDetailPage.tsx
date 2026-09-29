import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { LEAVE_TRANSITIONS, canWrite, label, money } from "../api/rules";
import type { ClaimSummary, Claimant, Leave, LeaveStatus, Page } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Alert, Card, Empty, Field, Loading, StatusBadge, errorText, useApi } from "../components/ui";

export default function EmployeeDetailPage() {
  const { claimantId } = useParams();
  const { role } = useAuth();
  const person = useApi(() => api<Claimant>(`/claimants/${claimantId}`), [claimantId]);
  const leaves = useApi(() => api<Leave[]>(`/claimants/${claimantId}/leaves`), [claimantId]);
  const claims = useApi(() => api<Page<ClaimSummary>>("/claims", { query: { claimant_id: claimantId, limit: 50 } }), [claimantId]);
  const [form, setForm] = useState({ leave_type: "FMLA", start_date: "", end_date: "", linked_claim_id: "", reason: "" });
  const [message, setMessage] = useState<{ kind: "error" | "success"; text: string } | null>(null);

  if (person.loading && !person.data) return <Loading />;
  if (person.error || !person.data) return <Alert>{person.error ?? "Employee not found"}</Alert>;
  const p = person.data;
  const stdClaims = (claims.data?.items ?? []).filter((c) => c.claim_type === "STD");

  async function act(action: () => Promise<unknown>, done: string) {
    setMessage(null);
    try {
      await action();
      setMessage({ kind: "success", text: done });
      void leaves.reload();
    } catch (e) {
      setMessage({ kind: "error", text: errorText(e) });
    }
  }

  function createLeave(e: FormEvent) {
    e.preventDefault();
    void act(
      () => api<Leave>("/leaves", {
        method: "POST",
        body: {
          claimant_id: p.claimant_id,
          leave_type: form.leave_type,
          start_date: form.start_date,
          end_date: form.end_date || null,
          linked_claim_id: form.linked_claim_id ? Number(form.linked_claim_id) : null,
          reason: form.reason || null,
        },
      }).then(() => setForm({ ...form, start_date: "", end_date: "", reason: "" })),
      "Leave request added.",
    );
  }

  const setLeaveStatus = (l: Leave, status: LeaveStatus) =>
    act(() => api(`/leaves/${l.leave_id}`, { method: "PATCH", body: { expected_version: l.version, status } }), `Leave ${label(status).toLowerCase()}.`);

  return (
    <>
      <p className="muted small"><Link to="/employees">Employees</Link> / {p.employee_number}</p>
      <h1>{p.first_name} {p.last_name}</h1>
      {message && <Alert kind={message.kind}>{message.text}</Alert>}

      <div className="grid-2">
        <Card title="Employee">
          <dl className="facts">
            <dt>Employee #</dt><dd>{p.employee_number}</dd>
            <dt>Hire date</dt><dd>{p.hire_date}</dd>
            <dt>Weekly salary</dt><dd>{money(p.weekly_salary)}</dd>
            <dt>Email</dt><dd>{p.email ?? "—"}</dd>
          </dl>
        </Card>
        <Card title="Claims">
          {claims.data?.items.length ? (
            <table>
              <tbody>
                {claims.data.items.map((c) => (
                  <tr key={c.claim_id}>
                    <td><Link to={`/claims/${c.claim_id}`}>{c.claim_number}</Link></td>
                    <td><StatusBadge status={c.status} /></td>
                    <td className="muted">{c.received_date}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <Empty>No claims.</Empty>}
        </Card>
      </div>

      <Card title="Leave">
        {leaves.loading ? <Loading /> : leaves.data?.length ? (
          <table>
            <thead><tr><th>Type</th><th>From</th><th>To</th><th>Status</th><th>Linked claim</th><th /></tr></thead>
            <tbody>
              {leaves.data.map((l) => (
                <tr key={l.leave_id}>
                  <td>{l.leave_type}</td>
                  <td>{l.start_date}</td>
                  <td>{l.end_date ?? "Open-ended"}</td>
                  <td><StatusBadge status={l.status} /></td>
                  <td>{l.linked_claim_id ? <Link to={`/claims/${l.linked_claim_id}`}>#{l.linked_claim_id}</Link> : "—"}</td>
                  <td className="btn-row">
                    {canWrite(role) && LEAVE_TRANSITIONS[l.status].map((s) => (
                      <button key={s} className="btn btn-ghost small" onClick={() => setLeaveStatus(l, s)}>{label(s)}</button>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <Empty>No leave on file.</Empty>}

        {canWrite(role) && (
          <form className="form grid-form top-gap" onSubmit={createLeave}>
            <Field label="Leave type">
              <select value={form.leave_type} onChange={(e) => setForm({ ...form, leave_type: e.target.value })}>
                <option value="FMLA">FMLA</option>
                <option value="MEDICAL">Medical</option>
                <option value="PERSONAL">Personal</option>
              </select>
            </Field>
            <Field label="Start"><input type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} required /></Field>
            <Field label="End" hint="Leave empty if not known yet"><input type="date" value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} /></Field>
            <Field label="Link to STD claim">
              <select value={form.linked_claim_id} onChange={(e) => setForm({ ...form, linked_claim_id: e.target.value })}>
                <option value="">None</option>
                {stdClaims.map((c) => <option key={c.claim_id} value={c.claim_id}>{c.claim_number}</option>)}
              </select>
            </Field>
            <Field label="Note"><input value={form.reason} maxLength={200} onChange={(e) => setForm({ ...form, reason: e.target.value })} /></Field>
            <div><button className="btn btn-primary">Add leave</button></div>
          </form>
        )}
      </Card>
    </>
  );
}
