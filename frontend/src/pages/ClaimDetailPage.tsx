import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { allowedClaimMoves, canWrite, label, money } from "../api/rules";
import type { ClaimDetail, ClaimStatus, Claimant } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Alert, Card, Empty, Field, Loading, StatusBadge, errorText, useApi } from "../components/ui";

export default function ClaimDetailPage() {
  const { claimId } = useParams();
  const { role } = useAuth();
  const claim = useApi(() => api<ClaimDetail>(`/claims/${claimId}`), [claimId]);
  const claimantId = claim.data?.claimant_id;
  const claimant = useApi(
    () => (claimantId ? api<Claimant>(`/claimants/${claimantId}`) : Promise.resolve(null)),
    [claimantId],
  );
  const [target, setTarget] = useState<ClaimStatus | null>(null);
  const [reason, setReason] = useState("");
  const [rtw, setRtw] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ kind: "error" | "success"; text: string } | null>(null);

  if (claim.loading && !claim.data) return <Loading />;
  if (claim.error || !claim.data) return <Alert>{claim.error ?? "Claim not found"}</Alert>;
  const c = claim.data;
  const moves = role ? allowedClaimMoves(c.status, role) : [];

  async function run(action: () => Promise<ClaimDetail>, done: string) {
    setBusy(true);
    setMessage(null);
    try {
      claim.setData(await action());
      setMessage({ kind: "success", text: done });
      setTarget(null);
      setReason("");
    } catch (e) {
      setMessage({ kind: "error", text: errorText(e) });
    } finally {
      setBusy(false);
    }
  }

  const changeStatus = () =>
    run(
      () => api<ClaimDetail>(`/claims/${c.claim_id}/status`, {
        method: "POST",
        body: { to_status: target, reason, expected_version: c.version },
      }),
      `Claim moved to ${label(target ?? "")}.`,
    );

  return (
    <>
      <div className="page-head">
        <div>
          <p className="muted small"><Link to="/claims">Claims</Link> / {c.claim_number}</p>
          <h1>{c.claim_number} <StatusBadge status={c.status} /></h1>
        </div>
      </div>
      {message && <Alert kind={message.kind}>{message.text}</Alert>}

      <div className="grid-2">
        <Card title="Summary">
          <dl className="facts">
            <dt>Type</dt><dd>{c.claim_type === "STD" ? "Short-Term Disability" : "Life insurance"}</dd>
            <dt>Employee</dt>
            <dd>
              {claimant.data ? (
                <Link to={`/employees/${c.claimant_id}`}>
                  {claimant.data.first_name} {claimant.data.last_name} ({claimant.data.employee_number})
                </Link>
              ) : `#${c.claimant_id}`}
            </dd>
            <dt>Received</dt><dd>{c.received_date}</dd>
            <dt>Assigned to</dt><dd>{c.assigned_to ?? "—"}</dd>
            <dt>Closed</dt><dd>{c.closed_date ?? "—"}</dd>
            <dt>Version</dt><dd>{c.version}</dd>
          </dl>
        </Card>

        <Card title="Actions">
          {moves.length === 0 ? (
            <Empty>{canWrite(role) ? "No status changes are allowed from here." : "Read-only access."}</Empty>
          ) : (
            <div className="stack">
              <div className="btn-row">
                {moves.map((m) => (
                  <button key={m} className={`btn ${target === m ? "btn-primary" : ""}`} onClick={() => setTarget(m)}>
                    Move to {label(m)}
                  </button>
                ))}
              </div>
              {target && (
                <>
                  <Field label={`Reason for moving to ${label(target)}`}>
                    <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={2} placeholder="Short note for the audit trail" />
                  </Field>
                  <div className="btn-row">
                    <button className="btn btn-primary" disabled={busy || reason.trim().length < 3} onClick={changeStatus}>
                      Confirm
                    </button>
                    <button className="btn btn-ghost" onClick={() => setTarget(null)}>Cancel</button>
                  </div>
                </>
              )}
            </div>
          )}
        </Card>
      </div>

      {c.std_detail && (
        <Card
          title="Short-Term Disability"
          actions={canWrite(role) && (
            <button className="btn" disabled={busy} onClick={() => run(
              () => api<ClaimDetail>(`/claims/${c.claim_id}/calculate-benefit`, { method: "POST" }),
              "Benefit calculated.",
            )}>
              Calculate benefit
            </button>
          )}
        >
          <dl className="facts">
            <dt>Disability start</dt><dd>{c.std_detail.disability_start_date}</dd>
            <dt>Condition group</dt><dd>{label(c.std_detail.condition_category)}</dd>
            <dt>Waiting period</dt><dd>{c.std_detail.elimination_days} days</dd>
            <dt>Benefits start</dt><dd>{c.std_detail.benefit_start_date ?? "Not calculated"}</dd>
            <dt>Weekly benefit</dt><dd>{money(c.std_detail.weekly_benefit)}</dd>
            <dt>Return to work</dt><dd>{c.std_detail.return_to_work_date ?? "—"}</dd>
          </dl>
          {canWrite(role) && (
            <div className="inline-form">
              <Field label="Set return-to-work date">
                <input type="date" value={rtw} onChange={(e) => setRtw(e.target.value)} />
              </Field>
              <button className="btn" disabled={!rtw || busy} onClick={() => run(
                () => api<ClaimDetail>(`/claims/${c.claim_id}/return-to-work`, {
                  method: "PUT", body: { return_to_work_date: rtw },
                }),
                "Return-to-work date saved.",
              )}>Save</button>
            </div>
          )}
        </Card>
      )}

      {c.life_detail && (
        <Card title="Life insurance">
          <dl className="facts">
            <dt>Date of death</dt><dd>{c.life_detail.date_of_death}</dd>
            <dt>Cause group</dt><dd>{label(c.life_detail.cause_category)}</dd>
            <dt>Payout</dt><dd>{money(c.life_detail.payout_amount)}</dd>
          </dl>
          <table>
            <thead><tr><th>Beneficiary</th><th>Relationship</th><th className="num">Share</th></tr></thead>
            <tbody>
              {c.beneficiaries.map((b) => (
                <tr key={b.beneficiary_id}>
                  <td>{b.full_name}</td><td>{label(b.relationship)}</td><td className="num">{b.share_pct}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      <div className="grid-2">
        <Card title="Status history">
          <ol className="timeline">
            {c.history.map((h, i) => (
              <li key={i}>
                <StatusBadge status={h.to_status} />
                <div>
                  <div>{h.reason ?? "—"}</div>
                  <div className="muted small">{h.changed_by} · {new Date(h.changed_at + "Z").toLocaleString()}</div>
                </div>
              </li>
            ))}
          </ol>
        </Card>
        <Card title="Payments">
          {c.payments.length === 0 ? <Empty>No payments yet.</Empty> : (
            <table>
              <thead><tr><th>Period</th><th className="num">Amount</th><th>Status</th></tr></thead>
              <tbody>
                {c.payments.map((p) => (
                  <tr key={p.payment_id}>
                    <td>{p.period_start ? `${p.period_start} → ${p.period_end}` : `Beneficiary #${p.beneficiary_id}`}</td>
                    <td className="num">{money(p.amount)}</td>
                    <td><StatusBadge status={p.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>
    </>
  );
}
