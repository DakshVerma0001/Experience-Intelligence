import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { clearSession, getUser } from "../services/auth";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/import", label: "Import Experience" },
  { to: "/imports", label: "Import History" },
  { to: "/review", label: "Review Queue", roles: ["REVIEWER", "ADMIN"] },
  { to: "/search", label: "Experience Search" },
  { to: "/settings", label: "Settings", roles: ["ADMIN"] },
  { to: "/audit", label: "Audit Logs", roles: ["ADMIN"] },
];

export default function Layout() {
  const navigate = useNavigate();
  const user = getUser();

  function logout() {
    clearSession();
    navigate("/login");
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          Experience Intelligence
          <small>Local AI Knowledge Import</small>
        </div>
        <nav className="sidebar-nav">
          {NAV_ITEMS.filter((item) => !item.roles || (user && item.roles.includes(user.role))).map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end}>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div>{user?.full_name}</div>
          <span className="role-badge">{user?.role}</span>
          <button onClick={logout}>Sign out</button>
        </div>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
