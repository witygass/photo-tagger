const BASE = "";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options?.headers ?? {}) },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(text || `HTTP ${res.status}`);
  }
  const ct = res.headers.get("content-type") ?? "";
  return ct.includes("application/json") ? res.json() : (res.text() as unknown as T);
}

export interface User {
  id: string;
  email: string;
  name: string | null;
  picture_url: string | null;
}

export interface Person {
  id: string;
  name: string;
  embedding_count: number;
  created_at: string;
}

export interface Embedding {
  id: string;
  photo_label: string | null;
  created_at: string;
}

export interface Folder {
  id: string;
  name: string;
  mime_type: string;
}

export interface FolderDetail {
  id: string;
  name: string;
  image_count: number;
}

export interface Job {
  id: string;
  folder_id: string;
  folder_name: string | null;
  status: "pending" | "running" | "done" | "error";
  total: number;
  processed: number;
  percent: number;
  error_msg: string | null;
  created_at: string;
  updated_at: string;
}

export interface Photo {
  id: string;
  drive_file_id: string;
  file_name: string | null;
  thumbnail_url: string | null;
  drive_link: string | null;
  people: string[];
}

export interface Results {
  job_id: string;
  total: number;
  page: number;
  page_size: number;
  people_in_job: string[];
  photos: Photo[];
}

// Auth
export const api = {
  auth: {
    me: () => request<User>("/auth/me"),
    logout: () => request<{ ok: boolean }>("/auth/logout", { method: "POST" }),
  },

  people: {
    list: () => request<Person[]>("/people/"),
    create: (name: string) =>
      request<Person>("/people/", { method: "POST", body: JSON.stringify({ name }) }),
    delete: (id: string) =>
      request<{ ok: boolean }>(`/people/${id}`, { method: "DELETE" }),
    uploadPhoto: (personId: string, file: File) => {
      const form = new FormData();
      form.append("photo", file);
      return fetch(`/people/${personId}/photos`, {
        method: "POST",
        credentials: "include",
        body: form,
      }).then(async (res) => {
        if (!res.ok) throw new Error(await res.text());
        return res.json() as Promise<Embedding>;
      });
    },
    deletePhoto: (personId: string, photoId: string) =>
      request<{ ok: boolean }>(`/people/${personId}/photos/${photoId}`, { method: "DELETE" }),
  },

  drive: {
    folders: (parentId = "root") =>
      request<Folder[]>(`/drive/folders?parent_id=${parentId}`),
    folderDetail: (id: string) =>
      request<FolderDetail>(`/drive/folders/${id}`),
  },

  jobs: {
    submit: (folderId: string) =>
      request<Job>("/jobs/", { method: "POST", body: JSON.stringify({ folder_id: folderId }) }),
    get: (id: string) => request<Job>(`/jobs/${id}`),
    list: () => request<Job[]>("/jobs/"),
    delete: (id: string) => request<{ ok: boolean }>(`/jobs/${id}`, { method: "DELETE" }),
    results: (id: string, people: string[] = [], exclusive = false, page = 1) => {
      const params = new URLSearchParams({ page: String(page), page_size: "50" });
      people.forEach((p) => params.append("people", p));
      if (exclusive) params.set("exclusive", "true");
      return request<Results>(`/jobs/${id}/results?${params}`);
    },
  },
};
