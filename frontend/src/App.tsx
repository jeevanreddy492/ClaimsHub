import { NavLink, Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { canWrite, label } from "./api/rules";
import { useAuth } from "./auth/AuthContext";
import ClaimDetailPage from "./pages/ClaimDetailPage";
import ClaimsPage from "./pages/ClaimsPage";
import DashboardPage from "./pages/DashboardPage";
import EmployeeDetailPage from "./pages/EmployeeDetailPage";
import EmployeesPage from "./pages/EmployeesPage";
import LoginPage from "./pages/LoginPage";
import NewLifeClaimPage from "./pages/NewLifeClaimPage";
import NewStdClaimPage from "./pages/NewStdClaimPage";
import SetupPage from "./pages/SetupPage";

function Layout() {
  const { session, role, logout } = useAuth();
  const location = useLocation();
  if (!session) return <Navigate to="/login" replace state={{ from: location.pathname }} />;

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <img src="/favicon.svg" alt="" width={28} height={28} />
          <span>ClaimsHub</span>
        </div>
        <nav>
          <NavLink to="/" end>Dashboard</NavLink>
          <NavLink to="/claims" end>Claims</NavLink>
          {canWrite(role) && <NavLink to="/claims/new/std">New STD claim</NavLink>}
          {canWrite(role) && <NavLink to="/claims/new/life">New Life claim</NavLink>}
          <NavLink to="/employees">Employees &amp; leave</NavLink>
          <NavLink to="/setup">Employers &amp; policies</NavLink>
        </nav>
        <div className="who">
          <div>{session.full_name}</div>
          <div className="muted small">{label(session.role)}</div>
          <button className="btn btn-ghost small" onClick={logout}>Sign out</button>
        </div>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="/claims" element={<ClaimsPage />} />
        <Route path="/claims/new/std" element={<NewStdClaimPage />} />
        <Route path="/claims/new/life" element={<NewLifeClaimPage />} />
        <Route path="/claims/:claimId" element={<ClaimDetailPage />} />
        <Route path="/employees" element={<EmployeesPage />} />
        <Route path="/employees/:claimantId" element={<EmployeeDetailPage />} />
        <Route path="/setup" element={<SetupPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
