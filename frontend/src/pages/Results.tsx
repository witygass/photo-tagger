import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, Photo, Results as ResultsType } from "../api";

export default function Results() {
  const { jobId } = useParams<{ jobId: string }>();
  const [results, setResults] = useState<ResultsType | null>(null);
  const [selectedPeople, setSelectedPeople] = useState<string[]>([]);
  const [exclusive, setExclusive] = useState(false);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  const load = (people: string[], excl: boolean, p: number) => {
    if (!jobId) return;
    setLoading(true);
    api.jobs
      .results(jobId, people, excl, p)
      .then(setResults)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load(selectedPeople, exclusive, page);
  }, [jobId, selectedPeople, exclusive, page]);

  const togglePerson = (person: string) => {
    setSelectedPeople((prev) =>
      prev.includes(person) ? prev.filter((p) => p !== person) : [...prev, person]
    );
    setPage(1);
  };

  const clearFilter = () => {
    setSelectedPeople([]);
    setExclusive(false);
    setPage(1);
  };

  if (!results && loading) return <div className="p-8 text-center text-gray-500">Loading...</div>;
  if (!results) return <div className="p-8 text-center text-red-500">Results not found.</div>;

  const totalPages = Math.ceil(results.total / results.page_size);

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="flex items-center gap-3 mb-6">
        <Link to="/dashboard" className="text-sm text-gray-500 hover:text-gray-700">
          ← Jobs
        </Link>
        <h1 className="text-2xl font-bold text-gray-900">Results</h1>
        <span className="text-gray-400 text-sm">{results.total} photos</span>
      </div>

      {/* Person filter pills */}
      {results.people_in_job.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 mb-6">
          <button
            onClick={clearFilter}
            className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
              selectedPeople.length === 0
                ? "bg-indigo-600 text-white"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            All
          </button>
          {results.people_in_job.map((person) => (
            <button
              key={person}
              onClick={() => togglePerson(person)}
              className={`px-3 py-1 rounded-full text-sm font-medium transition-colors capitalize ${
                selectedPeople.includes(person)
                  ? "bg-indigo-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              {person}
            </button>
          ))}
          {selectedPeople.length > 0 && (
            <label className="flex items-center gap-1.5 ml-2 text-sm text-gray-600 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={exclusive}
                onChange={(e) => { setExclusive(e.target.checked); setPage(1); }}
                className="rounded accent-indigo-600"
              />
              Only these people
            </label>
          )}
        </div>
      )}

      {loading ? (
        <div className="text-center text-gray-400 py-12">Loading...</div>
      ) : results.photos.length === 0 ? (
        <div className="text-center text-gray-400 py-12">
          {selectedPeople.length > 0 ? `No photos match the selected filter.` : "No photos processed."}
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
          {results.photos.map((photo) => (
            <PhotoCard key={photo.id} jobId={jobId!} photo={photo} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center items-center gap-3 mt-8">
          <button
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
            className="px-3 py-1 text-sm rounded border border-gray-300 disabled:opacity-40 hover:bg-gray-50"
          >
            Previous
          </button>
          <span className="text-sm text-gray-600">
            {page} / {totalPages}
          </span>
          <button
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
            className="px-3 py-1 text-sm rounded border border-gray-300 disabled:opacity-40 hover:bg-gray-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

function PhotoCard({ jobId, photo }: { jobId: string; photo: Photo }) {
  const src = photo.drive_file_id
    ? `/jobs/${jobId}/photos/${photo.id}/thumbnail`
    : null;
  return (
    <a
      href={photo.drive_link ?? "#"}
      target="_blank"
      rel="noopener noreferrer"
      className="group block rounded-xl overflow-hidden border border-gray-200 hover:border-indigo-400 transition-colors bg-white"
    >
      {src ? (
        <img
          src={src}
          alt={photo.file_name ?? "photo"}
          className="w-full aspect-square object-cover group-hover:opacity-90 transition-opacity"
          loading="lazy"
        />
      ) : (
        <div className="w-full aspect-square bg-gray-100 flex items-center justify-center text-gray-400 text-3xl">
          📷
        </div>
      )}
      <div className="p-2">
        <p className="text-xs text-gray-500 truncate">{photo.file_name}</p>
        {photo.people.length > 0 && (
          <p className="text-xs text-indigo-600 font-medium capitalize truncate">
            {photo.people.join(", ")}
          </p>
        )}
      </div>
    </a>
  );
}
