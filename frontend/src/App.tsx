import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./hooks/useAuth";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import People from "./pages/People";
import SelectFolder from "./pages/SelectFolder";
import JobStatus from "./pages/JobStatus";
import Results from "./pages/Results";
import NavBar from "./components/NavBar";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="flex items-center justify-center h-screen text-gray-500">Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <div className="min-h-screen bg-gray-50">
                <NavBar />
                <Routes>
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/people" element={<People />} />
                  <Route path="/select-folder" element={<SelectFolder />} />
                  <Route path="/jobs/:jobId" element={<JobStatus />} />
                  <Route path="/jobs/:jobId/results" element={<Results />} />
                  <Route path="/" element={<Navigate to="/dashboard" replace />} />
                </Routes>
              </div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
