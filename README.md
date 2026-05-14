# Photo Tagger

AI-powered face recognition for your Google Drive photos. Sign in with Google, teach the app who your known people are, select a Drive folder, and it will scan every photo and tag who appears in each one. Browse results filtered by person — no photos are ever stored on the server.

## How it works

1. **Add known people** — Upload a few clear, front-facing reference photos per person. The app extracts face embeddings (mathematical fingerprints) and stores only those; the photos themselves are immediately discarded.
2. **Select a folder** — Browse your Google Drive and pick a folder to process.
3. **Let it run** — The app downloads Drive thumbnails, runs face recognition against your known people, and records the results. A live progress bar tracks the job.
4. **Browse results** — View all photos in a grid, filter by person with one click, and open any photo directly in Google Drive.

## Tech stack

- **Backend**: Python / FastAPI, InsightFace (`buffalo_l` model), Pets-Face-Recognition (dog/cat), SQLAlchemy, SQLite (dev) / PostgreSQL (prod)
- **Frontend**: React, TypeScript, Vite, Tailwind CSS
- **Auth**: Google OAuth 2.0 (web flow); tokens encrypted at rest with Fernet

---

## Prerequisites

- Python 3.11+
- Node.js 20+
- A Google Cloud project with the Drive API and Google People API enabled
- A **Web application** OAuth 2.0 client ID ([create one here](https://console.cloud.google.com/apis/credentials))

> **Note:** The existing `credentials.json` in this repo is for the CLI tool (Desktop app type). The web app requires a separate **Web application** client ID with a redirect URI.

---

## Local development setup

### 1. Configure Google OAuth

In [Google Cloud Console](https://console.cloud.google.com/apis/credentials):

1. Create a new OAuth 2.0 Client ID — type: **Web application**
2. Add `http://localhost:8000/auth/callback` under **Authorized redirect URIs**
3. Copy the Client ID and Client Secret

### 2. Create your `.env` file

```bash
cp .env.example .env
```

Fill in the required values:

```bash
# Generate these two keys:
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=<fernet-key>
# python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=<hex-string>

GOOGLE_CLIENT_ID=<your-web-client-id>.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-<...>
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
```

The remaining values in `.env.example` have working defaults for local development.

### 3. Initialise submodules

The pet recognition library is included as a git submodule:

```bash
git submodule update --init
```

Then download the pet recognition model checkpoints (~1 GB, hosted on Zenodo):

```bash
source .venv/bin/activate && cd backend/third_party/pets_face_recognition && python3 download_models.py && cd -
```

If you skip this step the app still works — pet recognition will be silently disabled.

### 4. Run the backend

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
PYTHONPATH=backend uvicorn app.main:app --reload --app-dir backend
```

The first startup downloads the InsightFace model (~500 MB) and creates the SQLite database automatically.

### 5. Run the frontend

In a separate terminal:

```bash
npm install --prefix frontend
npm run dev --prefix frontend
```

Open [http://localhost:5173](http://localhost:5173).

---

## Running with Docker

```bash
git submodule update --init
docker-compose up
```

This starts the backend (port 8000), PostgreSQL, and the frontend dev server (port 5173) together. The InsightFace model is pre-downloaded during the image build and cached in a named volume so it survives container restarts.

Make sure your `.env` file is present in the repo root before running.

---

## Deployment (Railway)

1. Push the repo to GitHub.
2. Create a new Railway project and add a service pointed at the `backend/` subdirectory — Railway detects the `Dockerfile` automatically.
3. Add the **PostgreSQL** plugin; Railway injects `DATABASE_URL` automatically.
4. Set all required environment variables in Railway's dashboard (`ENCRYPTION_KEY`, `SECRET_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `FRONTEND_URL`, `ALLOWED_ORIGINS`).
5. Deploy the frontend (`frontend/`) as a static site on Vercel or Netlify (`npm run build`, publish `dist/`). Set `VITE_API_URL` to your Railway backend URL.
6. Add your production callback URL (`https://yourdomain.com/auth/callback`) to the authorized redirect URIs in Google Cloud Console.

---

## CLI tool

The original command-line tagger still works independently:

```bash
pip install -r requirements.txt
python3 tag.py --folder-id <DRIVE_FOLDER_ID>
```

See `SETUP.md` for CLI-specific setup instructions.

---

## Privacy

- Reference photos are processed to extract face embeddings, then **immediately deleted**. Only the embeddings (float arrays) are persisted.
- Processed photos are never stored. The app records file IDs, filenames, and Google-hosted thumbnail URLs — no image data.
- Google OAuth tokens are encrypted at rest using Fernet symmetric encryption.
