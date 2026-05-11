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
  const [selected, setSelected] = useState<Map<string, Folder>>(new Map());
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
  };

  const navigateTo = (idx: number) => {
    const bc = breadcrumbs.slice(0, idx + 1);
    setBreadcrumbs(bc);
    setParentId(bc[bc.length - 1].id);
  };

  const toggleSelect = (folder: Folder) => {
    setSelected((prev) => {
      const next = new Map(prev);
      if (next.has(folder.id)) {
        next.delete(folder.id);
      } else {
        next.set(folder.id, folder);
      }
      return next;
    });
  };

  const submit = async () => {
    if (selected.size === 0) return;
    setSubmitting(true);
    setError("");
    try {
      await Promise.all([...selected.values()].map((f) => api.jobs.submit(f.id)));
      navigate("/dashboard");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start job");
      setSubmitting(false);
    }
  };

  const selectedFolders = [...selected.values()];

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Select Folders to Tag</h1>
      <p className="text-gray-500 text-sm mb-6">
        Choose one or more Google Drive folders. All photos inside will be scanned for known people.
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
            {folders.map((folder) => {
              const isSelected = selected.has(folder.id);
              return (
                <li
                  key={folder.id}
                  className={`flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-gray-50 transition-colors ${
                    isSelected ? "bg-indigo-50" : ""
                  }`}
                  onClick={() => toggleSelect(folder)}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => toggleSelect(folder)}
                    onClick={(e) => e.stopPropagation()}
                    className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 cursor-pointer"
                  />
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
              );
            })}
          </ul>
        )}
      </div>

      {selectedFolders.length > 0 && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4 mb-4">
          <div className="flex items-center justify-between gap-4 mb-3">
            <div className="text-sm font-medium text-gray-900">
              {selectedFolders.length} folder{selectedFolders.length > 1 ? "s" : ""} selected
            </div>
            <button
              onClick={submit}
              disabled={submitting}
              className="bg-indigo-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors shrink-0"
            >
              {submitting
                ? "Starting..."
                : `Start Tagging${selectedFolders.length > 1 ? ` (${selectedFolders.length})` : ""}`}
            </button>
          </div>
          <ul className="flex flex-wrap gap-2">
            {selectedFolders.map((f) => (
              <li
                key={f.id}
                className="flex items-center gap-1 bg-white border border-indigo-200 rounded-full px-3 py-1 text-xs text-gray-700"
              >
                <span>📁</span>
                <span>{f.name}</span>
                <button
                  onClick={() => toggleSelect(f)}
                  className="ml-1 text-gray-400 hover:text-gray-700"
                  aria-label={`Remove ${f.name}`}
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {error && <p className="text-red-600 text-sm">{error}</p>}
    </div>
  );
}
