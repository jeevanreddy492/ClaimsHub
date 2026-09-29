import { useCallback, useEffect, useState, type ReactNode } from "react";
import { ApiError } from "../api/client";
import { label } from "../api/rules";

/** Load data from the API with loading/error state and a reload function. */
export function useApi<T>(load: () => Promise<T>, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(load, deps);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await run());
    } catch (e) {
      setError(errorText(e));
    } finally {
      setLoading(false);
    }
  }, [run]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { data, error, loading, reload, setData };
}

export function errorText(e: unknown): string {
  if (e instanceof ApiError) return e.describe();
  return e instanceof Error ? e.message : "Something went wrong";
}

export function StatusBadge({ status }: { status: string }) {
  return <span className={`badge badge-${status.toLowerCase()}`}>{label(status)}</span>;
}

export function Alert({ kind = "error", children }: { kind?: "error" | "success" | "info"; children: ReactNode }) {
  if (!children) return null;
  return (
    <div className={`alert alert-${kind}`} role={kind === "error" ? "alert" : "status"}>
      {children}
    </div>
  );
}

export function Card({ title, actions, children }: { title?: string; actions?: ReactNode; children: ReactNode }) {
  return (
    <section className="card">
      {(title || actions) && (
        <header className="card-head">
          {title && <h2>{title}</h2>}
          {actions && <div className="card-actions">{actions}</div>}
        </header>
      )}
      {children}
    </section>
  );
}

/**
 * Form field with a label. Use `group` when the children hold buttons: a <label>
 * forwards clicks to the first button inside it, which fires the wrong action.
 */
export function Field({ label: text, children, hint, group = false }: { label: string; children: ReactNode; hint?: string; group?: boolean }) {
  const inner = (
    <>
      <span className="field-label">{text}</span>
      {children}
      {hint && <span className="field-hint">{hint}</span>}
    </>
  );
  return group ? <div className="field" role="group" aria-label={text}>{inner}</div> : <label className="field">{inner}</label>;
}

export function Loading() {
  return <p className="muted">Loading…</p>;
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="muted empty">{children}</p>;
}

export function Pager({ total, limit, offset, onChange }: { total: number; limit: number; offset: number; onChange: (offset: number) => void }) {
  if (total <= limit) return null;
  const page = Math.floor(offset / limit) + 1;
  const pages = Math.ceil(total / limit);
  return (
    <div className="pager">
      <button className="btn btn-ghost" disabled={offset === 0} onClick={() => onChange(Math.max(0, offset - limit))}>
        Previous
      </button>
      <span className="muted">
        Page {page} of {pages} · {total} total
      </span>
      <button className="btn btn-ghost" disabled={offset + limit >= total} onClick={() => onChange(offset + limit)}>
        Next
      </button>
    </div>
  );
}
