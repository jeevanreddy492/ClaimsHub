import { useState, type FormEvent } from "react";
import { api } from "../api/client";
import { canWrite, money } from "../api/rules";
import type { Employer, Policy } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Alert, Card, Empty, Field, errorText, useApi } from "../components/ui";

export default function SetupPage() {
  const { role } = useAuth();
  const employers = useApi(() => api<Employer[]>("/employers"), []);
  const policies = useApi(() => api<Policy[]>("/policies"), []);
  const [emp, setEmp] = useState({ name: "", tax_id: "" });
  const [pol, setPol] = useState({ employer_id: "", product_type: "STD", effective_date: "", benefit_pct: "60", max_weekly_benefit: "1500", elimination_days: "7", max_benefit_weeks: "26", face_amount: "100000" });
  const [message, setMessage] = useState<{ kind: "error" | "success"; text: string } | null>(null);

  async function act(action: () => Promise<unknown>, done: string) {
    setMessage(null);
    try {
      await action();
      setMessage({ kind: "success", text: done });
      void employers.reload();
      void policies.reload();
    } catch (e) {
      setMessage({ kind: "error", text: errorText(e) });
    }
  }

  function addEmployer(e: FormEvent) {
    e.preventDefault();
    void act(() => api("/employers", { method: "POST", body: emp }).then(() => setEmp({ name: "", tax_id: "" })), "Employer added.");
  }

  function addPolicy(e: FormEvent) {
    e.preventDefault();
    const isStd = pol.product_type === "STD";
    const body = {
      employer_id: Number(pol.employer_id),
      product_type: pol.product_type,
      effective_date: pol.effective_date,
      ...(isStd
        ? { benefit_pct: pol.benefit_pct, max_weekly_benefit: pol.max_weekly_benefit, elimination_days: Number(pol.elimination_days), max_benefit_weeks: Number(pol.max_benefit_weeks) }
        : { face_amount: pol.face_amount }),
    };
    void act(() => api("/policies", { method: "POST", body }), "Policy added.");
  }

  const employerName = (id: number) => employers.data?.find((e) => e.employer_id === id)?.name ?? `#${id}`;

  return (
    <>
      <h1>Employers &amp; policies</h1>
      {message && <Alert kind={message.kind}>{message.text}</Alert>}
      <div className="grid-2">
        <Card title="Employers">
          {employers.data?.length ? (
            <ul className="plain">{employers.data.map((e) => <li key={e.employer_id}>{e.name}</li>)}</ul>
          ) : <Empty>No employers yet.</Empty>}
          {canWrite(role) && (
            <form className="form top-gap" onSubmit={addEmployer}>
              <Field label="Employer name"><input value={emp.name} onChange={(e) => setEmp({ ...emp, name: e.target.value })} required minLength={2} /></Field>
              <Field label="Tax ID" hint="Format 12-3456789 (fake)"><input value={emp.tax_id} onChange={(e) => setEmp({ ...emp, tax_id: e.target.value })} required pattern="\d{2}-\d{7}" /></Field>
              <div><button className="btn btn-primary">Add employer</button></div>
            </form>
          )}
        </Card>

        {canWrite(role) && (
          <Card title="New policy">
            <form className="form" onSubmit={addPolicy}>
              <Field label="Employer">
                <select value={pol.employer_id} onChange={(e) => setPol({ ...pol, employer_id: e.target.value })} required>
                  <option value="">Pick an employer</option>
                  {(employers.data ?? []).map((e) => <option key={e.employer_id} value={e.employer_id}>{e.name}</option>)}
                </select>
              </Field>
              <Field label="Product">
                <select value={pol.product_type} onChange={(e) => setPol({ ...pol, product_type: e.target.value })}>
                  <option value="STD">Short-Term Disability</option>
                  <option value="LIFE">Life</option>
                </select>
              </Field>
              <Field label="Effective date"><input type="date" value={pol.effective_date} onChange={(e) => setPol({ ...pol, effective_date: e.target.value })} required /></Field>
              {pol.product_type === "STD" ? (
                <div className="grid-2 tight">
                  <Field label="Benefit %"><input value={pol.benefit_pct} onChange={(e) => setPol({ ...pol, benefit_pct: e.target.value })} /></Field>
                  <Field label="Max weekly ($)"><input value={pol.max_weekly_benefit} onChange={(e) => setPol({ ...pol, max_weekly_benefit: e.target.value })} /></Field>
                  <Field label="Waiting days"><input value={pol.elimination_days} onChange={(e) => setPol({ ...pol, elimination_days: e.target.value })} /></Field>
                  <Field label="Max weeks"><input value={pol.max_benefit_weeks} onChange={(e) => setPol({ ...pol, max_benefit_weeks: e.target.value })} /></Field>
                </div>
              ) : (
                <Field label="Face amount ($)"><input value={pol.face_amount} onChange={(e) => setPol({ ...pol, face_amount: e.target.value })} /></Field>
              )}
              <div><button className="btn btn-primary">Add policy</button></div>
            </form>
          </Card>
        )}
      </div>

      <Card title="Policies">
        {policies.data?.length ? (
          <table>
            <thead><tr><th>Policy</th><th>Employer</th><th>Product</th><th>Terms</th><th>Effective</th></tr></thead>
            <tbody>
              {policies.data.map((p) => (
                <tr key={p.policy_id}>
                  <td>{p.policy_number}</td>
                  <td>{employerName(p.employer_id)}</td>
                  <td>{p.product_type}</td>
                  <td>{p.product_type === "STD" ? `${p.benefit_pct}% up to ${money(p.max_weekly_benefit)}/wk, ${p.elimination_days}-day wait` : money(p.face_amount)}</td>
                  <td>{p.effective_date}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <Empty>No policies yet.</Empty>}
      </Card>
    </>
  );
}
