import sqlite3, json, os, subprocess

db = 'cloud_jobs.db'
tracker = '.db_status_tracker.json'

# 1. Pull latest snapshot from Modal volume
subprocess.run(
    ["modal", "volume", "get", "--force", "job-hunt-db", "jobs.db", db],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
)

if not os.path.exists(db):
    print("❌ Failed to download cloud_jobs.db from Modal.")
    exit(1)

# 2. Fetch current counts
conn = sqlite3.connect(db)
counts = dict(conn.cursor().execute("SELECT status, COUNT(*) FROM jobs GROUP BY status").fetchall())

curr_apply = counts.get('APPLY', 0)
curr_notified = counts.get('NOTIFIED', 0)
curr_rejected = counts.get('REJECTED', 0)
curr_total = sum(counts.values())

# 3. Read previous state
prev = {'APPLY': 0, 'NOTIFIED': 0, 'REJECTED': 0, 'TOTAL': 0}
if os.path.exists(tracker):
    try:
        with open(tracker, 'r') as f:
            prev = json.load(f)
    except Exception:
        pass

# 4. Save current state
with open(tracker, 'w') as f:
    json.dump({'APPLY': curr_apply, 'NOTIFIED': curr_notified, 'REJECTED': curr_rejected, 'TOTAL': curr_total}, f)

diff_a = curr_apply - prev.get('APPLY', 0)
diff_n = curr_notified - prev.get('NOTIFIED', 0)
diff_r = curr_rejected - prev.get('REJECTED', 0)
diff_t = curr_total - prev.get('TOTAL', 0)

fmt = lambda d: f"+{d}" if d > 0 else str(d)

print('==============================================')
print('         CLOUD DATABASE AUDIT METRICS         ')
print('==============================================')
print(' STATUS     │ CURRENT  │ PREVIOUS │ DELTA')
print('────────────┼──────────┼──────────┼───────────')
print(f' APPLY      │ {curr_apply:<8} │ {prev.get("APPLY", 0):<8} │ {fmt(diff_a)}')
print(f' NOTIFIED   │ {curr_notified:<8} │ {prev.get("NOTIFIED", 0):<8} │ {fmt(diff_n)}')
print(f' REJECTED   │ {curr_rejected:<8} │ {prev.get("REJECTED", 0):<8} │ {fmt(diff_r)}')
print('────────────┼──────────┼──────────┼───────────')
print(f' TOTAL JOBS │ {curr_total:<8} │ {prev.get("TOTAL", 0):<8} │ {fmt(diff_t)}')
print('==============================================')

if diff_a > 0 or diff_n > 0:
    print(f'\n🚨 NEW MATCHES DISCOVERED! (+{diff_a} APPLY, +{diff_n} NOTIFIED)')
    rows = conn.cursor().execute("SELECT scouted_at, status, company, title FROM jobs WHERE status IN ('APPLY', 'NOTIFIED') ORDER BY scouted_at DESC LIMIT ?", (diff_a + diff_n,)).fetchall()
    for r in rows:
        print(f'   - [{r[1]}] [{r[0]}] {r[2]}: {r[3]}')
elif diff_t > 0:
    print(f'\nℹ️ Scraped {diff_t} new job listings, but all were marked REJECTED.')
else:
    print('\n✅ No database changes detected since last check.')
