import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, Folder } from "../api";

export default function SelectFolder() {
  const [folders, setFolders] = useState<Folder[]>([]);
  const [parentId, setParentId] = useState("root");
  const [breadcrumbs, setBreadcrumbs] = useState<Array<{ id: string; name: string }>>([
    { id: "root", name: "My Drive" },
  ]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Folder | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    setLoading(true);
    api.drive
      .folders(parentId)
      .then(setFolders)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [parentId]);

  const navigateInto = (folder: Folder) => {
    setBreadcrumbs((prev) => [...prev, { id: folder.id, name: folder.name }]);
    setParentId(folder.id);
    setSelected(null);
  };

  const navigateTo = (idx: number) => {
    const bc = breadcrumbs.slice(0, idx + 1);
    setBreadcrumbs(bc);
    setParentId(bc[bc.length - 1].id);
    setSelected(null);
  };

  const submit = async () => {
    if (!selected) return;
    setSubmitting(true);
    setError("");
    try {
      const job = await api.jobs.submit(selected.id);
      navigate(`/jobs/${job.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start job");
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Select a Folder to Tag</h1>
      <p className="text-gray-500 text-sm mb-6">
        Choose a Google Drive folder. All photos inside will be scanned for known people.
      </p>

      {/* Breadcrumbs */}
      <div className="flex items-center gap-1 text-sm text-gray-500 mb-3 flex-wrap">
        {breadcrumbs.map((bc, idx) => (
          <span key={bc.id} className="flex items-center gap-1">
            {idx > 0 && <span>/</span>}
            <button
              className={`hover:text-indigo-600 ${idx === breadcrumbs.length - 1 ? "font-medium text-gray-800" : ""}`}
              onClick={() => navigateTo(idx)}
            >
              {bc.name}
            </button>
          </span>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden mb-6">
        {loading ? (
          <div className="p-8 text-center text-gray-400">Loading folders...</div>
        ) : folders.length === 0 ? (
          <div className="p-8 text-center text-gray-400">No sub-folders here.</div>
        ) : (
          <ul className="divide-y divide-gray-100">
            {folders.map((folder) => (
              <li
                key={folder.id}
                className={`flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-gray-50 transition-colors ${
                  selected?.id === folder.id ? "bg-indigo-50" : ""
                }`}
                onClick={() => setSelected(folder)}
              >
                <span className="text-xl">📁</span>
                <span className="flex-1 text-sm font-medium text-gray-800">{folder.name}</span>
                <button
                  className="text-xs text-indigo-500 hover:text-indigo-700 shrink-0"
                  onClick={(e) => {
                    e.stopPropagation();
                    navigateInto(folder);
                  }}
                >
                  Open →
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {selected && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4 flex items-center gap-4 mb-4">
          <span className="text-xl">📁</span>
          <div className="flex-1">
            <div className="font-medium text-gray-900">{selected.name}</div>
            <div className="text-sm text-indigo-600">Selected for tagging</div>
          </div>
          <button
            onClick={submit}
            disabled={submitting}
            className="bg-indigo-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {submitting ? "Starting..." : "Start Tagging"}
          </button>
        </div>
      )}

      {error && <p className="text-red-600 text-sm">{error}</p>}
    </div>
  );
}
