import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { label } from "../api/rules";
import type { ClaimSummary, Page } from "../api/types";
import { Alert, Card, Empty, Field, Loading, Pager, StatusBadge, useApi } from "../components/ui";

const LIMIT = 20;
const STATUSES = ["RECEIVED", "IN_REVIEW", "APPROVED", "DENIED", "APPEALED", "CLOSED"];

export default function ClaimsPage() {
  const [params, setParams] = useSearchParams();
  const status = params.get("status") ?? "";
  const claimType = params.get("type") ?? "";
  const claimNumber = params.get("number") ?? "";
  const offset = Number(params.get("offset") ?? 0);
  const [numberInput, setNumberInput] = useState(claimNumber);

  const claims = useApi(
    () =>
      api<Page<ClaimSummary>>("/claims", {
        query: { status, claim_type: claimType, claim_number: claimNumber, limit: LIMIT, offset },
      }),
    [status, claimType, claimNumber, offset],
  );

  function update(next: Record<string, string>) {
    const merged: Record<string, string> = { status, type: claimType, number: claimNumber, ...next };
    if (!("offset" in next)) merged.offset = "0";
    setParams(Object.fromEntries(Object.entries(merged).filter(([, v]) => v && v !== "0")));
  }

  function searchNumber(e: FormEvent) {
    e.preventDefault();
    update({ number: numberInput.trim() });
  }

  return (
    <>
      <h1>Claims</h1>
      <Card>
        <div className="filters">
          <Field label="Status">
            <select value={status} onChange={(e) => update({ status: e.target.value })}>
              <option value="">All</option>
              {STATUSES.map((s) => <option key={s} value={s}>{label(s)}</option>)}
            </select>
          </Field>
          <Field label="Type">
            <select value={claimType} onChange={(e) => update({ type: e.target.value })}>
              <option value="">All</option>
              <option value="STD">Short-Term Disability</option>
              <option value="LIFE">Life</option>
            </select>
          </Field>
          <form onSubmit={searchNumber} className="inline-form">
            <Field label="Claim number">
              <input placeholder="STD-2026-000123" value={numberInput} onChange={(e) => setNumberInput(e.target.value)} />
            </Field>
            <button className="btn">Find</button>
          </form>
        </div>
      </Card>
      <Alert>{claims.error}</Alert>
      <Card>
        {claims.loading ? <Loading /> : claims.data?.items.length ? (
          <>
            <table>
              <thead>
                <tr><th>Claim</th><th>Type</th><th>Status</th><th>Received</th><th>Assigned to</th><th>Updated</th></tr>
              </thead>
              <tbody>
                {claims.data.items.map((c) => (
                  <tr key={c.claim_id}>
                    <td><Link to={`/claims/${c.claim_id}`}>{c.claim_number}</Link></td>
                    <td>{c.claim_type}</td>
                    <td><StatusBadge status={c.status} /></td>
                    <td>{c.received_date}</td>
                    <td>{c.assigned_to ?? "—"}</td>
                    <td className="muted">{new Date(c.updated_at + "Z").toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Pager total={claims.data.total} limit={LIMIT} offset={offset} onChange={(o) => update({ offset: String(o) })} />
          </>
        ) : <Empty>No claims match these filters.</Empty>}
      </Card>
    </>
  );
}
