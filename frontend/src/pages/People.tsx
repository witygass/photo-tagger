import { useEffect, useRef, useState } from "react";
import { api, Person } from "../api";

export default function People() {
  const [people, setPeople] = useState<Person[]>([]);
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const [uploadingFor, setUploadingFor] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState<{ current: number; total: number } | null>(null);
  const [uploadError, setUploadError] = useState<Record<string, string>>({});
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [pendingPersonId, setPendingPersonId] = useState<string | null>(null);

  const reload = () =>
    api.people.list().then(setPeople).finally(() => setLoading(false));

  useEffect(() => {
    reload();
  }, []);

  const createPerson = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    setError("");
    try {
      await api.people.create(newName.trim());
      setNewName("");
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create person");
    } finally {
      setCreating(false);
    }
  };

  const deletePerson = async (id: string, name: string) => {
    if (!confirm(`Delete "${name}" and all their reference photos?`)) return;
    await api.people.delete(id);
    await reload();
  };

  const triggerUpload = (personId: string) => {
    setPendingPersonId(personId);
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    if (!files.length || !pendingPersonId) return;
    e.target.value = "";

    const personId = pendingPersonId;
    setUploadingFor(personId);
    setUploadProgress({ current: 0, total: files.length });
    setUploadError((prev) => ({ ...prev, [personId]: "" }));

    const errors: string[] = [];
    for (let i = 0; i < files.length; i++) {
      setUploadProgress({ current: i + 1, total: files.length });
      try {
        await api.people.uploadPhoto(personId, files[i]);
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Upload failed";
        errors.push(`${files[i].name}: ${msg}`);
      }
    }

    if (errors.length) {
      setUploadError((prev) => ({ ...prev, [personId]: errors.join("; ") }));
    }
    await reload();
    setUploadingFor(null);
    setUploadProgress(null);
    setPendingPersonId(null);
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Known People</h1>

      {/* Add person form */}
      <form onSubmit={createPerson} className="flex gap-2 mb-8">
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="Person's name (e.g. Tyler)"
          className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
        />
        <button
          type="submit"
          disabled={creating || !newName.trim()}
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
        >
          Add Person
        </button>
      </form>
      {error && <p className="text-red-600 text-sm mb-4">{error}</p>}

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        multiple
        className="hidden"
        onChange={handleFileChange}
      />

      {loading ? (
        <div className="text-gray-500">Loading...</div>
      ) : people.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-10 text-center">
          <div className="text-4xl mb-3">👤</div>
          <p className="text-gray-500 text-sm">
            No known people yet. Add someone above and upload reference photos so the AI can recognize them.
          </p>
        </div>
      ) : (
        <div className="grid gap-4">
          {people.map((person) => (
            <div
              key={person.id}
              className="bg-white rounded-xl border border-gray-200 p-4 flex items-center gap-4"
            >
              <div className="w-12 h-12 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-700 font-bold text-lg uppercase shrink-0">
                {person.name[0]}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium text-gray-900">{person.name}</div>
                <div className="text-sm text-gray-500">
                  {person.embedding_count} reference photo{person.embedding_count !== 1 ? "s" : ""}
                </div>
                {uploadError[person.id] && (
                  <p className="text-red-500 text-xs mt-1">{uploadError[person.id]}</p>
                )}
              </div>
              <button
                onClick={() => triggerUpload(person.id)}
                disabled={uploadingFor === person.id}
                className="text-sm text-indigo-600 hover:underline disabled:opacity-50 shrink-0"
              >
                {uploadingFor === person.id
                  ? uploadProgress && uploadProgress.total > 1
                    ? `Uploading ${uploadProgress.current}/${uploadProgress.total}...`
                    : "Uploading..."
                  : "+ Add photo"}
              </button>
              <button
                onClick={() => deletePerson(person.id, person.name)}
                className="text-sm text-red-500 hover:text-red-700 shrink-0"
              >
                Delete
              </button>
            </div>
          ))}
        </div>
      )}

      {people.length > 0 && (
        <p className="text-xs text-gray-400 mt-6">
          Tip: Add 3–5 clear, front-facing photos per person for best accuracy.
        </p>
      )}
    </div>
  );
}
