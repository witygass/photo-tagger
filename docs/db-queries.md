# Database Query Reference

The production database is Postgres; local dev uses SQLite (same schema, same queries).

Connect:
```bash
# Docker (docker-compose)
docker compose exec db psql -U postgres -d photo_tagger

# local SQLite
sqlite3 backend/photo_tagger.db

# Postgres (Railway or otherwise)
psql $DATABASE_URL
```

---

## Schema

```
users
  id              TEXT  PK
  google_id       TEXT  UNIQUE
  email           TEXT
  name            TEXT
  picture_url     TEXT
  encrypted_token BLOB
  token_updated_at TIMESTAMP
  created_at      TIMESTAMP

known_people
  id         TEXT  PK
  user_id    TEXT  FK → users.id
  name       TEXT
  species    TEXT  -- "human" | "dog" | "cat"
  created_at TIMESTAMP

reference_embeddings
  id          TEXT  PK
  person_id   TEXT  FK → known_people.id
  embedding   BLOB  -- serialized numpy float32 array
  photo_label TEXT
  created_at  TIMESTAMP

jobs
  id          TEXT  PK
  user_id     TEXT  FK → users.id
  folder_id   TEXT  -- Google Drive folder ID
  folder_name TEXT
  status      TEXT  -- "pending" | "running" | "done" | "error"
  total       INT   -- total photos in folder
  processed   INT   -- photos processed so far
  error_msg   TEXT
  created_at  TIMESTAMP
  updated_at  TIMESTAMP

tagged_photos
  id            TEXT  PK
  job_id        TEXT  FK → jobs.id
  user_id       TEXT  FK → users.id
  drive_file_id TEXT  -- Google Drive file ID (also the thumbnail cache key)
  file_name     TEXT
  thumbnail_url TEXT  -- Drive thumbnailLink (may expire)
  drive_link    TEXT
  people        TEXT  -- comma-separated names, e.g. "Alice,Bob" or ""
  processed_at  TIMESTAMP
```

> **Note on `people`:** names are stored as a plain comma-separated string with no spaces around commas. An empty string means no one was recognised. Use `LIKE` or `string_split` to query individuals (see examples below).

---

## Common queries

### Users

```sql
-- all users
SELECT id, email, name, created_at FROM users ORDER BY created_at DESC;

-- find by email
SELECT * FROM users WHERE email = 'alice@example.com';
```

### Jobs

```sql
-- all jobs for a user
SELECT id, folder_name, status, processed, total, created_at
FROM jobs
WHERE user_id = '<user_id>'
ORDER BY created_at DESC;

-- stuck / in-flight jobs
SELECT id, user_id, folder_name, status, updated_at
FROM jobs
WHERE status IN ('pending', 'running')
ORDER BY updated_at;

-- jobs with errors
SELECT id, user_id, folder_name, error_msg, updated_at
FROM jobs
WHERE status = 'error';

-- job throughput: photos per job
SELECT id, folder_name, processed, total,
       ROUND(processed * 100.0 / NULLIF(total, 0), 1) AS pct
FROM jobs
WHERE status = 'done'
ORDER BY created_at DESC;
```

### Tagged photos

```sql
-- all photos from a job
SELECT id, file_name, people, drive_link
FROM tagged_photos
WHERE job_id = '<job_id>'
ORDER BY processed_at;

-- photos containing a specific person (Postgres)
SELECT tp.file_name, tp.people, tp.drive_link
FROM tagged_photos tp
WHERE tp.job_id = '<job_id>'
  AND (
    tp.people = 'Alice'
    OR tp.people LIKE 'Alice,%'
    OR tp.people LIKE '%,Alice'
    OR tp.people LIKE '%,Alice,%'
  );

-- photos with no one recognised
SELECT file_name, drive_link
FROM tagged_photos
WHERE job_id = '<job_id>' AND people = '';

-- person frequency across an entire job
-- (Postgres: unnest on string_to_array)
SELECT name, COUNT(*) AS appearances
FROM (
  SELECT TRIM(unnest(string_to_array(people, ','))) AS name
  FROM tagged_photos
  WHERE job_id = '<job_id>' AND people <> ''
) sub
GROUP BY name
ORDER BY appearances DESC;

-- same thing in SQLite
SELECT name, COUNT(*) AS appearances
FROM (
  SELECT TRIM(value) AS name
  FROM tagged_photos, json_each('["' || REPLACE(people, ',', '","') || '"]')
  WHERE job_id = '<job_id>' AND people <> ''
) sub
GROUP BY name
ORDER BY appearances DESC;
```

### Known people & embeddings

```sql
-- all known people for a user
SELECT kp.name, kp.species, COUNT(re.id) AS reference_count
FROM known_people kp
LEFT JOIN reference_embeddings re ON re.person_id = kp.id
WHERE kp.user_id = '<user_id>'
GROUP BY kp.id, kp.name, kp.species
ORDER BY kp.name;

-- people with no reference embeddings (can't be recognised)
SELECT kp.id, kp.name
FROM known_people kp
LEFT JOIN reference_embeddings re ON re.person_id = kp.id
WHERE kp.user_id = '<user_id>' AND re.id IS NULL;
```

### Cross-table

```sql
-- full picture: user → jobs → photo counts
SELECT u.email, j.folder_name, j.status,
       COUNT(tp.id) AS photos_tagged,
       j.created_at
FROM users u
JOIN jobs j ON j.user_id = u.id
LEFT JOIN tagged_photos tp ON tp.job_id = j.id
GROUP BY u.email, j.id, j.folder_name, j.status, j.created_at
ORDER BY j.created_at DESC;
```

---

## Thumbnail cache

Thumbnails are cached to disk at `THUMBNAIL_CACHE_DIR` (default `/tmp/photo_tagger_thumbnails`) as `<drive_file_id>.jpg`. If you need to bust the cache for a photo, delete the corresponding file:

```bash
rm /tmp/photo_tagger_thumbnails/<drive_file_id>.jpg
```
