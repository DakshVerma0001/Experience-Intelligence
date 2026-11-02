import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import type { Role } from "../types";
import { getToken, getUser } from "../services/auth";

export default function RequireAuth({ children, roles }: { children: ReactNode; roles?: Role[] }) {
  const token = getToken();
  const user = getUser();
  if (!token || !user) {
    return <Navigate to="/login" replace />;
  }
  if (roles && !roles.includes(user.role)) {
    return (
      <div className="card">
        <h2>Access denied</h2>
        <p>Your role ({user.role}) does not have access to this page.</p>
      </div>
    );
  }
  return <>{children}</>;
}
