import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import RequireAuth from "./components/RequireAuth";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import ImportExperience from "./pages/ImportExperience";
import ImportHistory from "./pages/ImportHistory";
import ImportDetails from "./pages/ImportDetails";
import ReviewQueue from "./pages/ReviewQueue";
import ProjectReview from "./pages/ProjectReview";
import SearchExperience from "./pages/SearchExperience";
import Settings from "./pages/Settings";
import AuditLogs from "./pages/AuditLogs";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          element={
            <RequireAuth>
              <Layout />
            </RequireAuth>
          }
        >
          <Route path="/" element={<Dashboard />} />
          <Route path="/import" element={<ImportExperience />} />
          <Route path="/imports" element={<ImportHistory />} />
          <Route path="/imports/:batchId" element={<ImportDetails />} />
          <Route
            path="/review"
            element={
              <RequireAuth roles={["REVIEWER", "ADMIN"]}>
                <ReviewQueue />
              </RequireAuth>
            }
          />
          <Route path="/projects/:projectId" element={<ProjectReview />} />
          <Route path="/search" element={<SearchExperience />} />
          <Route
            path="/settings"
            element={
              <RequireAuth roles={["ADMIN"]}>
                <Settings />
              </RequireAuth>
            }
          />
          <Route
            path="/audit"
            element={
              <RequireAuth roles={["ADMIN"]}>
                <AuditLogs />
              </RequireAuth>
            }
          />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
