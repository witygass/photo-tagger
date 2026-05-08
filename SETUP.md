# photo-tagger setup

## 1. Install dependencies

```bash
cd ~/Repos/photo-tagger
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Google Cloud credentials

1. Go to https://console.cloud.google.com
2. Create a project (or use an existing one)
3. Enable the **Google Drive API**
4. Go to **APIs & Services > Credentials > Create Credentials > OAuth 2.0 Client ID**
5. Application type: **Desktop app**
6. Download the JSON and save it as `credentials.json` in this folder

## 3. Add known people

Create a subfolder in `known_people/` for each person, with 3–5 clear face photos:

```
known_people/
  tyler/
    photo1.jpg
    photo2.jpg
  mom/
    photo1.jpg
```

More reference photos = better accuracy. Use front-facing, well-lit shots.

## 4. Get your Drive folder ID

Open the target folder in Google Drive. The URL looks like:
`https://drive.google.com/drive/folders/1aBcDeFgHiJkLmNoPqRsTuVwXyZ`

The folder ID is the last segment: `1aBcDeFgHiJkLmNoPqRsTuVwXyZ`

## 5. Run

```bash
# First run — will open browser for Google auth
python3 tag.py --folder-id 1yT1ljy7Wx8_iI5McFHM6fOHtEquBNYMa

# Dry run (no writes to Drive)
python3 tag.py --folder-id 1yT1ljy7Wx8_iI5McFHM6fOHtEquBNYMa --dry-run

# Reprocess everything (ignore cache)
python3 tag.py --folder-id 1yT1ljy7Wx8_iI5McFHM6fOHtEquBNYMa --reprocess
```

Tags are written to each file's Drive properties under the key `tagged_people`
as a comma-separated string (e.g. `tyler,mom`). You can view them via the
Drive API or build a search on top later.

## Tuning accuracy

Edit `recognizer.py` and adjust `SIMILARITY_THRESHOLD` (line ~12):
- Lower value (e.g. `0.35`) = stricter, fewer false positives
- Higher value (e.g. `0.55`) = looser, catches more but may misidentify
