import { useMemo, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api, newCorrelationId } from "../api/client";
import { label } from "../api/rules";
import type { ClaimDetail, Claimant, Policy } from "../api/types";
import { EmployeePicker } from "../components/EmployeePicker";
import { Alert, Card, Field, errorText, useApi } from "../components/ui";

const CONDITIONS = ["MUSCULOSKELETAL", "SURGERY", "MATERNITY", "INJURY", "CARDIAC", "MENTAL_HEALTH", "OTHER"];

export default function NewStdClaimPage() {
  const navigate = useNavigate();
  const [employee, setEmployee] = useState<Claimant | null>(null);
  const [policyId, setPolicyId] = useState("");
  const [start, setStart] = useState("");
  const [condition, setCondition] = useState("MUSCULOSKELETAL");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // One key per form: a double click or a retry after a timeout never makes two claims.
  const idempotencyKey = useMemo(() => newCorrelationId(), []);

  const employerId = employee?.employer_id;
  const policies = useApi(
    () => (employerId ? api<Policy[]>("/policies", { query: { employer_id: employerId, product_type: "STD" } }) : Promise.resolve([])),
    [employerId],
  );

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!employee) return;
    setBusy(true);
    setError(null);
    try {
      const claim = await api<ClaimDetail>("/claims/std", {
        method: "POST",
        headers: { "Idempotency-Key": idempotencyKey },
        body: { claimant_id: employee.claimant_id, policy_id: Number(policyId), disability_start_date: start, condition_category: condition },
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
      <h1>New Short-Term Disability claim</h1>
      <Alert>{error}</Alert>
      <Card>
        <form className="form" onSubmit={submit}>
          <EmployeePicker value={employee} onChange={(c) => { setEmployee(c); setPolicyId(""); }} />
          <Field label="STD policy">
            <select value={policyId} onChange={(e) => setPolicyId(e.target.value)} required disabled={!employee}>
              <option value="">{employee ? "Pick a policy" : "Pick an employee first"}</option>
              {(policies.data ?? []).map((p) => (
                <option key={p.policy_id} value={p.policy_id}>
                  {p.policy_number} · {p.benefit_pct}% up to ${p.max_weekly_benefit}/week · {p.elimination_days}-day wait
                </option>
              ))}
            </select>
          </Field>
          <Field label="First day unable to work">
            <input type="date" value={start} onChange={(e) => setStart(e.target.value)} required />
          </Field>
          <Field label="Condition group" hint="Only a category. Never enter medical details here.">
            <select value={condition} onChange={(e) => setCondition(e.target.value)}>
              {CONDITIONS.map((c) => <option key={c} value={c}>{label(c)}</option>)}
            </select>
          </Field>
          <button className="btn btn-primary" disabled={busy || !employee || !policyId || !start}>
            {busy ? "Filing…" : "File claim"}
          </button>
        </form>
      </Card>
    </>
  );
}
