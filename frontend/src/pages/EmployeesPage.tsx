import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { canWrite } from "../api/rules";
import type { Claimant, Employer, Page } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Alert, Card, Empty, Field, Loading, Pager, errorText, useApi } from "../components/ui";

const LIMIT = 20;
const blank = { employer_id: "", employee_number: "", first_name: "", last_name: "", date_of_birth: "", hire_date: "", weekly_salary: "", email: "" };

export default function EmployeesPage() {
  const { role } = useAuth();
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(blank);
  const [message, setMessage] = useState<{ kind: "error" | "success"; text: string } | null>(null);

  const employers = useApi(() => api<Employer[]>("/employers"), []);
  const list = useApi(() => api<Page<Claimant>>("/claimants", { query: { q: query, limit: LIMIT, offset } }), [query, offset]);
  const employerName = (id: number) => employers.data?.find((e) => e.employer_id === id)?.name ?? `#${id}`;

  async function create(e: FormEvent) {
    e.preventDefault();
    setMessage(null);
    try {
      const c = await api<Claimant>("/claimants", {
        method: "POST",
        body: { ...form, employer_id: Number(form.employer_id), email: form.email || null },
      });
      setMessage({ kind: "success", text: `Added ${c.first_name} ${c.last_name}.` });
      setForm(blank);
      setShowForm(false);
      void list.reload();
    } catch (err) {
      setMessage({ kind: "error", text: errorText(err) });
    }
  }

  const set = (k: keyof typeof blank) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value });

  return (
    <>
      <div className="page-head">
        <h1>Employees &amp; leave</h1>
        {canWrite(role) && <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>{showForm ? "Close" : "Add employee"}</button>}
      </div>
      {message && <Alert kind={message.kind}>{message.text}</Alert>}

      {showForm && (
        <Card title="New employee">
          <form className="form grid-form" onSubmit={create}>
            <Field label="Employer">
              <select value={form.employer_id} onChange={set("employer_id")} required>
                <option value="">Pick an employer</option>
                {(employers.data ?? []).map((e) => <option key={e.employer_id} value={e.employer_id}>{e.name}</option>)}
              </select>
            </Field>
            <Field label="Employee number"><input value={form.employee_number} onChange={set("employee_number")} required /></Field>
            <Field label="First name"><input value={form.first_name} onChange={set("first_name")} required /></Field>
            <Field label="Last name"><input value={form.last_name} onChange={set("last_name")} required /></Field>
            <Field label="Date of birth"><input type="date" value={form.date_of_birth} onChange={set("date_of_birth")} required /></Field>
            <Field label="Hire date"><input type="date" value={form.hire_date} onChange={set("hire_date")} required /></Field>
            <Field label="Weekly salary ($)"><input inputMode="decimal" value={form.weekly_salary} onChange={set("weekly_salary")} required /></Field>
            <Field label="Email (optional)"><input type="email" value={form.email} onChange={set("email")} /></Field>
            <div><button className="btn btn-primary">Save employee</button></div>
          </form>
        </Card>
      )}

      <Card>
        <form className="inline-form" onSubmit={(e) => { e.preventDefault(); setOffset(0); setQuery(q.trim()); }}>
          <Field label="Search"><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Name or employee number" /></Field>
          <button className="btn">Search</button>
        </form>
        <Alert>{list.error}</Alert>
        {list.loading ? <Loading /> : list.data?.items.length ? (
          <>
            <table>
              <thead><tr><th>Name</th><th>Employee #</th><th>Employer</th><th>Hire date</th></tr></thead>
              <tbody>
                {list.data.items.map((c) => (
                  <tr key={c.claimant_id}>
                    <td><Link to={`/employees/${c.claimant_id}`}>{c.last_name}, {c.first_name}</Link></td>
                    <td>{c.employee_number}</td>
                    <td>{employerName(c.employer_id)}</td>
                    <td>{c.hire_date}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Pager total={list.data.total} limit={LIMIT} offset={offset} onChange={setOffset} />
          </>
        ) : <Empty>No employees found.</Empty>}
      </Card>
    </>
  );
}
