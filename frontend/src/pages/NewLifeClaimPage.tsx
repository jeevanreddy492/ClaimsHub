import { useMemo, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api, newCorrelationId } from "../api/client";
import { money, sharesTotal } from "../api/rules";
import type { ClaimDetail, Claimant, Policy } from "../api/types";
import { EmployeePicker } from "../components/EmployeePicker";
import { Alert, Card, Field, errorText, useApi } from "../components/ui";

interface BeneficiaryRow {
  full_name: string;
  relationship: string;
  share_pct: string;
}

const RELATIONSHIPS = ["SPOUSE", "CHILD", "PARENT", "SIBLING", "OTHER"];
const emptyRow = (): BeneficiaryRow => ({ full_name: "", relationship: "SPOUSE", share_pct: "" });

export default function NewLifeClaimPage() {
  const navigate = useNavigate();
  const [employee, setEmployee] = useState<Claimant | null>(null);
  const [policyId, setPolicyId] = useState("");
  const [dateOfDeath, setDateOfDeath] = useState("");
  const [cause, setCause] = useState("NATURAL");
  const [rows, setRows] = useState<BeneficiaryRow[]>([{ ...emptyRow(), share_pct: "100" }]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const idempotencyKey = useMemo(() => newCorrelationId(), []);

  const employerId = employee?.employer_id;
  const policies = useApi(
    () => (employerId ? api<Policy[]>("/policies", { query: { employer_id: employerId, product_type: "LIFE" } }) : Promise.resolve([])),
    [employerId],
  );
  const total = sharesTotal(rows.map((r) => r.share_pct));

  function setRow(i: number, patch: Partial<BeneficiaryRow>) {
    setRows((rs) => rs.map((r, j) => (j === i ? { ...r, ...patch } : r)));
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!employee) return;
    setBusy(true);
    setError(null);
    try {
      const claim = await api<ClaimDetail>("/claims/life", {
        method: "POST",
        headers: { "Idempotency-Key": idempotencyKey },
        body: {
          claimant_id: employee.claimant_id,
          policy_id: Number(policyId),
          date_of_death: dateOfDeath,
          cause_category: cause,
          beneficiaries: rows,
        },
      });
      navigate(`/claims/${claim.claim_id}`);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h1>New Life insurance claim</h1>
      <Alert>{error}</Alert>
      <Card>
        <form className="form" onSubmit={submit}>
          <EmployeePicker value={employee} onChange={(c) => { setEmployee(c); setPolicyId(""); }} />
          <Field label="Life policy">
            <select value={policyId} onChange={(e) => setPolicyId(e.target.value)} required disabled={!employee}>
              <option value="">{employee ? "Pick a policy" : "Pick an employee first"}</option>
              {(policies.data ?? []).map((p) => (
                <option key={p.policy_id} value={p.policy_id}>{p.policy_number} · {money(p.face_amount)}</option>
              ))}
            </select>
          </Field>
          <div className="grid-2 tight">
            <Field label="Date of death">
              <input type="date" value={dateOfDeath} onChange={(e) => setDateOfDeath(e.target.value)} required />
            </Field>
            <Field label="Cause group">
              <select value={cause} onChange={(e) => setCause(e.target.value)}>
                <option value="NATURAL">Natural</option>
                <option value="ILLNESS">Illness</option>
                <option value="ACCIDENT">Accident</option>
              </select>
            </Field>
          </div>

          <h3>Beneficiaries</h3>
          <table className="edit-table">
            <thead><tr><th>Full name</th><th>Relationship</th><th className="num">Share %</th><th /></tr></thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  <td><input value={r.full_name} onChange={(e) => setRow(i, { full_name: e.target.value })} required aria-label="Beneficiary name" /></td>
                  <td>
                    <select value={r.relationship} onChange={(e) => setRow(i, { relationship: e.target.value })} aria-label="Relationship">
                      {RELATIONSHIPS.map((x) => <option key={x}>{x}</option>)}
                    </select>
                  </td>
                  <td><input className="num" inputMode="decimal" value={r.share_pct} onChange={(e) => setRow(i, { share_pct: e.target.value })} required aria-label="Share percent" /></td>
                  <td>{rows.length > 1 && <button type="button" className="btn btn-ghost small" onClick={() => setRows(rows.filter((_, j) => j !== i))}>Remove</button>}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="btn-row spread">
            <button type="button" className="btn" onClick={() => setRows([...rows, emptyRow()])} disabled={rows.length >= 10}>Add beneficiary</button>
            <span className={total === 100 ? "ok" : "warn"}>Total: {total}% {total === 100 ? "✓" : "(must be 100%)"}</span>
          </div>
          <button className="btn btn-primary" disabled={busy || !employee || !policyId || !dateOfDeath || total !== 100}>
            {busy ? "Filing…" : "File claim"}
          </button>
        </form>
      </Card>
    </>
  );
}
