import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export default function NavBar() {
  const { user, logout } = useAuth();
  const { pathname } = useLocation();

  const link = (to: string, label: string) => (
    <Link
      to={to}
      className={`px-3 py-2 rounded text-sm font-medium transition-colors ${
        pathname.startsWith(to)
          ? "bg-indigo-700 text-white"
          : "text-indigo-100 hover:bg-indigo-600"
      }`}
    >
      {label}
    </Link>
  );

  return (
    <nav className="bg-indigo-800 text-white px-4 py-3 flex items-center gap-4">
      <Link to="/dashboard" className="font-bold text-lg tracking-tight mr-4">
        Photo Tagger
      </Link>
      {link("/people", "Known People")}
      {link("/select-folder", "Tag Folder")}
      {link("/dashboard", "Jobs")}
      <div className="ml-auto flex items-center gap-3">
        {user?.picture_url && (
          <img src={user.picture_url} alt="" className="w-8 h-8 rounded-full" />
        )}
        <span className="text-sm text-indigo-200">{user?.name ?? user?.email}</span>
        <button
          onClick={logout}
          className="text-sm text-indigo-300 hover:text-white transition-colors"
        >
          Sign out
        </button>
      </div>
    </nav>
  );
}
