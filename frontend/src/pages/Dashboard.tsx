import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, Job } from "../api";

const STATUS_COLOR: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  running: "bg-blue-100 text-blue-800",
  done: "bg-green-100 text-green-800",
  error: "bg-red-100 text-red-800",
};

type SortKey = "name" | "date" | "status" | "count";

function sortJobs(jobs: Job[], key: SortKey): Job[] {
  return [...jobs].sort((a, b) => {
    switch (key) {
      case "name":
        return (a.folder_name ?? a.folder_id).localeCompare(b.folder_name ?? b.folder_id);
      case "date":
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      case "status":
        return a.status.localeCompare(b.status);
      case "count":
        return b.total - a.total;
    }
  });
}

export default function Dashboard() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("name");

  const reload = () =>
    api.jobs.list().then(setJobs).catch(console.error).finally(() => setLoading(false));

  useEffect(() => {
    reload();
  }, []);

  const deleteJob = async (id: string) => {
    if (!confirm("Delete this job and all its results?")) return;
    setDeletingId(id);
    try {
      await api.jobs.delete(id);
      await reload();
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Recent Jobs</h1>
        <div className="flex items-center gap-3">
          <select
            value={sortKey}
            onChange={(e) => setSortKey(e.target.value as SortKey)}
            className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 text-gray-600 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-300"
          >
            <option value="name">Sort: Folder name</option>
            <option value="date">Sort: Date</option>
            <option value="status">Sort: Status</option>
            <option value="count">Sort: Photo count</option>
          </select>
          <Link
            to="/select-folder"
            className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
          >
            + Tag a Folder
          </Link>
        </div>
      </div>

      {loading ? (
        <div className="text-gray-500">Loading...</div>
      ) : jobs.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-10 text-center">
          <div className="text-4xl mb-3">📂</div>
          <p className="text-gray-600 mb-4">No jobs yet.</p>
          <Link
            to="/select-folder"
            className="bg-indigo-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
          >
            Tag your first folder
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {sortJobs(jobs, sortKey).map((job) => (
            <div
              key={job.id}
              className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-4"
            >
              <div className="flex-1 min-w-0">
                <div className="font-medium text-gray-900 truncate">
                  {job.folder_name ?? job.folder_id}
                </div>
                <div className="text-sm text-gray-500">
                  {job.processed} / {job.total} photos &middot;{" "}
                  {new Date(job.created_at).toLocaleDateString()}
                </div>
              </div>
              <span
                className={`text-xs font-semibold px-2 py-1 rounded-full ${STATUS_COLOR[job.status] ?? "bg-gray-100 text-gray-600"}`}
              >
                {job.status}
              </span>
              {job.status === "done" && (
                <Link
                  to={`/jobs/${job.id}/results`}
                  className="text-sm text-indigo-600 hover:underline shrink-0"
                >
                  View results →
                </Link>
              )}
              {(job.status === "pending" || job.status === "running") && (
                <Link
                  to={`/jobs/${job.id}`}
                  className="text-sm text-indigo-600 hover:underline shrink-0"
                >
                  View progress →
                </Link>
              )}
              <button
                onClick={() => deleteJob(job.id)}
                disabled={deletingId === job.id}
                className="text-sm text-red-500 hover:text-red-700 disabled:opacity-50 shrink-0"
              >
                {deletingId === job.id ? "Deleting…" : "Delete"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
