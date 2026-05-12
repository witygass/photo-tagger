# Database Guide

The app uses SQLite by default. The file is at `backend/photo_tagger.db`.

## Open the database

```bash
cd backend
sqlite3 photo_tagger.db
```

Useful sqlite3 settings to run first:

```sql
.headers on
.mode column
```

## Tables

| Table | Description |
|---|---|
| `users` | Authenticated Google users |
| `known_people` | People/pets registered for recognition |
| `reference_embeddings` | Face embedding vectors per person |
| `jobs` | Tagging jobs (one per folder submission) |
| `tagged_photos` | Individual photos with matched people |

## Common queries

**List all users:**
```sql
SELECT id, email, name, created_at FROM users;
```

**List jobs with progress:**
```sql
SELECT id, folder_name, status, processed, total, error_msg, created_at
FROM jobs
ORDER BY created_at DESC;
```

**Find stuck jobs (pending/running after a restart):**
```sql
SELECT id, folder_name, status, processed, total FROM jobs
WHERE status IN ('pending', 'running');
```

**See all photos tagged in a job:**
```sql
SELECT file_name, people, drive_link FROM tagged_photos
WHERE job_id = '<job_id>';
```

**Find all photos containing a specific person:**
```sql
SELECT file_name, people, drive_link FROM tagged_photos
WHERE people = 'Tyler'
   OR people LIKE 'Tyler,%'
   OR people LIKE '%,Tyler,%'
   OR people LIKE '%,Tyler';
```

**Count photos per person across all jobs:**
```sql
SELECT people, COUNT(*) as count FROM tagged_photos
WHERE people != ''
GROUP BY people
ORDER BY count DESC;
```

**List known people and their reference photo counts:**
```sql
SELECT p.name, p.species, COUNT(e.id) as embeddings
FROM known_people p
LEFT JOIN reference_embeddings e ON e.person_id = p.id
GROUP BY p.id
ORDER BY p.name;
```

## Migrations

Migrations are managed with Alembic from the `backend/` directory.

**Apply all pending migrations:**
```bash
cd backend
alembic upgrade head
```

**Check current migration version:**
```bash
alembic current
```

**Roll back one migration:**
```bash
alembic downgrade -1
```

## Reset the database (destructive)

Deletes all data and recreates the schema from scratch.

```bash
cd backend
rm photo_tagger.db
alembic upgrade head
```
