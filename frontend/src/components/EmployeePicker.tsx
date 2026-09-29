import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Claimant, Page } from "../api/types";
import { Field } from "./ui";

/** Search employees by name or employee number and pick one. */
export function EmployeePicker({ value, onChange }: { value: Claimant | null; onChange: (c: Claimant | null) => void }) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<Claimant[]>([]);

  useEffect(() => {
    if (value || q.trim().length < 2) {
      setResults([]);
      return;
    }
    const t = setTimeout(() => {
      api<Page<Claimant>>("/claimants", { query: { q: q.trim(), limit: 8 } })
        .then((p) => setResults(p.items))
        .catch(() => setResults([]));
    }, 250);
    return () => clearTimeout(t);
  }, [q, value]);

  if (value) {
    return (
      <Field label="Employee" group>
        <div className="picked">
          <span>{value.first_name} {value.last_name} · {value.employee_number}</span>
          <button type="button" className="btn btn-ghost small" onClick={() => onChange(null)}>Change</button>
        </div>
      </Field>
    );
  }
  return (
    <Field label="Employee" group hint="Type at least 2 letters of the name or employee number">
      <div className="picker">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search employees" aria-label="Search employees" />
        {results.length > 0 && (
          <ul className="picker-list">
            {results.map((c) => (
              <li key={c.claimant_id}>
                <button type="button" onClick={() => onChange(c)}>
                  {c.first_name} {c.last_name} <span className="muted">· {c.employee_number}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Field>
  );
}
