# Tazkirim Monitor

Monitor [tazkirim.gov.il](https://www.tazkirim.gov.il/) for new legislation related to electric vehicles and electricity regulations, then send push notifications via [ntfy](https://ntfy.sh/).

## What it does

1. Searches the government legislation site for configured Hebrew keywords.
2. Collects matching documents from search results.
3. Keeps only items whose **publication date (`תאריך הפצה`) is today** in `Asia/Jerusalem`.
4. Sends one ntfy notification per new item (deduplicated in SQLite).

## Requirements

- Python 3.10+
- Chromium (installed via Playwright)

## Setup

```powershell
cd c:\Users\igorve\source\repos\tazkirim-monitor
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\pip install -e .
.\.venv\Scripts\playwright install chromium
copy .env.example .env
```

Edit `.env` and set a private topic name:

```env
NTFY_SERVER=https://ntfy.sh
NTFY_TOPIC=your-secret-topic-name
```

Subscribe to that topic in the ntfy mobile app (or any ntfy client).

## Usage

Dry run (no notifications):

```powershell
.\.venv\Scripts\python -m tazkirim_monitor --dry-run
```

Include all dates (useful for testing):

```powershell
.\.venv\Scripts\python -m tazkirim_monitor --dry-run --all-dates
```

Filter by a specific date:

```powershell
.\.venv\Scripts\python -m tazkirim_monitor --dry-run --date 2026-03-10
```

Send notifications:

```powershell
.\.venv\Scripts\python -m tazkirim_monitor
```

Debug screenshot after the last query:

```powershell
.\.venv\Scripts\python -m tazkirim_monitor --dry-run --debug-screenshot debug.png
```

## Default search terms

- עמדת טעינה
- תקנות החשמל
- תקנות משק החשמל
- תקנות מקורות האנרגיה
- טעינת רכב חשמלי
- לרכב חשמלי
- טעינת רכבים חשמיללים
- רכב חשמלי

Override via `.env`:

```env
SEARCH_QUERIES=עמדת טעינה,תקנות החשמל
```

## Windows Task Scheduler

Recommended schedule: 3 times per day (08:00, 12:00, 17:00 Israel time).

1. Open **Task Scheduler** → **Create Task**
2. **General**
   - Name: `Tazkirim Monitor`
   - Run whether user is logged on or not
3. **Triggers** → New → Daily, repeat 3 times (or create 3 separate triggers)
4. **Actions** → New
   - Program/script: `C:\Users\igorve\source\repos\tazkirim-monitor\.venv\Scripts\python.exe`
   - Add arguments: `-m tazkirim_monitor`
   - Start in: `C:\Users\igorve\source\repos\tazkirim-monitor`
5. **Settings**
   - Allow task to be run on demand
   - If the task fails, restart every 15 minutes (optional)

Ensure `.env` exists in the project folder before scheduling.

## ntfy subscription

1. Install the ntfy app (Android/iOS) or use the web UI.
2. Subscribe to the same topic configured in `NTFY_TOPIC`.
3. Pick a hard-to-guess topic name (it acts as a password on the public ntfy.sh service).

Optional self-hosted server:

```env
NTFY_SERVER=https://ntfy.example.com
```

## Configuration reference

| Variable | Default | Description |
|---|---|---|
| `NTFY_SERVER` | `https://ntfy.sh` | ntfy server URL |
| `NTFY_TOPIC` | _(required)_ | Topic name |
| `NTFY_PRIORITY` | `4` | Notification priority (1-5) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `STATE_DB_PATH` | `./data/state.db` | SQLite dedupe database |
| `SEARCH_QUERIES` | built-in list | Comma-separated search terms |
| `SEND_HEARTBEAT` | `false` | Send ntfy when no new items |
| `PAGE_LOAD_TIMEOUT_MS` | `60000` | Playwright timeout |
| `SEARCH_WAIT_MS` | `12000` | Wait after submitting search |
| `MAX_LOAD_MORE_CLICKS` | `20` | Max pagination clicks per query |

## How search works

The site is a Salesforce Experience Cloud app. Search is performed through the homepage free-text search box (`חיפוש חופשי`), not the `/global-search/` URL (which returns no document results).

Publication date is parsed from each result card line:

```text
כ"א אדר התשפ"ו|10/03/2026|13:33|משרד האנרגיה|...
```

The Gregorian date (`10/03/2026`) is used for the "published today" filter.

## License

Private utility project.
