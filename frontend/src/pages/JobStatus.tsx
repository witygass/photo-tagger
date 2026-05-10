import { useEffect } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useJob } from "../hooks/useJob";

export default function JobStatus() {
  const { jobId } = useParams<{ jobId: string }>();
  const { job, loading } = useJob(jobId);
  const navigate = useNavigate();

  useEffect(() => {
    if (job?.status === "done") {
      const t = setTimeout(() => navigate(`/jobs/${jobId}/results`), 1500);
      return () => clearTimeout(t);
    }
  }, [job?.status, jobId, navigate]);

  if (loading) return <div className="p-8 text-center text-gray-500">Loading...</div>;
  if (!job) return <div className="p-8 text-center text-red-500">Job not found.</div>;

  return (
    <div className="max-w-xl mx-auto px-4 py-12">
      <div className="bg-white rounded-2xl border border-gray-200 p-8">
        <h1 className="text-xl font-bold text-gray-900 mb-1">
          {job.folder_name ?? "Processing..."}
        </h1>
        <p className="text-sm text-gray-500 mb-6">
          {job.status === "done"
            ? "Complete! Redirecting to results..."
            : job.status === "error"
              ? "An error occurred."
              : `Processing photos...`}
        </p>

        {/* Progress bar */}
        <div className="w-full bg-gray-200 rounded-full h-3 mb-3">
          <div
            className={`h-3 rounded-full transition-all duration-500 ${
              job.status === "error" ? "bg-red-500" : "bg-indigo-500"
            }`}
            style={{ width: `${job.percent}%` }}
          />
        </div>
        <div className="flex justify-between text-sm text-gray-500 mb-6">
          <span>
            {job.processed} / {job.total} photos
          </span>
          <span>{job.percent}%</span>
        </div>

        {job.status === "error" && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700 mb-4">
            {job.error_msg ?? "Unknown error"}
          </div>
        )}

        <div className="flex gap-3">
          <Link
            to="/dashboard"
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            ← Back to jobs
          </Link>
          {job.status === "done" && (
            <Link
              to={`/jobs/${job.id}/results`}
              className="text-sm text-indigo-600 font-medium hover:underline"
            >
              View results →
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
