import { Link } from "react-router-dom";
import { api } from "../api/client";
import { label } from "../api/rules";
import type { ClaimStats, ClaimStatus, ClaimSummary, Page } from "../api/types";
import { Alert, Card, Empty, Loading, StatusBadge, useApi } from "../components/ui";

const ORDER: ClaimStatus[] = ["RECEIVED", "IN_REVIEW", "APPROVED", "DENIED", "APPEALED", "CLOSED"];

export default function DashboardPage() {
  const stats = useApi(() => api<ClaimStats>("/claims/stats"), []);
  const recent = useApi(() => api<Page<ClaimSummary>>("/claims", { query: { limit: 8 } }), []);

  return (
    <>
      <h1>Dashboard</h1>
      <Alert>{stats.error || recent.error}</Alert>
      <div className="stats">
        <Link to="/claims" className="stat">
          <span className="stat-label">All claims</span>
          <span className="stat-value">{stats.data?.total ?? "—"}</span>
          <span className="muted small">
            STD {stats.data?.by_type.STD ?? 0} · Life {stats.data?.by_type.LIFE ?? 0}
          </span>
        </Link>
        {ORDER.map((s) => (
          <Link to={`/claims?status=${s}`} className="stat" key={s}>
            <span className="stat-label">{label(s)}</span>
            <span className="stat-value">{stats.data?.by_status[s] ?? 0}</span>
          </Link>
        ))}
      </div>
      <Card title="Latest claims" actions={<Link to="/claims">See all</Link>}>
        {recent.loading ? <Loading /> : recent.data?.items.length ? (
          <table>
            <thead>
              <tr><th>Claim</th><th>Type</th><th>Status</th><th>Received</th><th>Assigned to</th></tr>
            </thead>
            <tbody>
              {recent.data.items.map((c) => (
                <tr key={c.claim_id}>
                  <td><Link to={`/claims/${c.claim_id}`}>{c.claim_number}</Link></td>
                  <td>{c.claim_type}</td>
                  <td><StatusBadge status={c.status} /></td>
                  <td>{c.received_date}</td>
                  <td>{c.assigned_to ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <Empty>No claims yet.</Empty>}
      </Card>
    </>
  );
}
