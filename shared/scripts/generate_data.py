"""
What this file does:
  Creates 5 fake (synthetic) CSV files in shared/data/raw/ — hcp, products,
  prescriptions, engagements, territory_map. No real patient / pharma data.

Why fake data:
  You cannot use real pharma data. Synthetic data lets you practise
  Bronze -> Silver -> Gold with known answers: you already know Silver
  must come out at 762, quarantine at 38. If your pipeline gives a
  different number, your pipeline is wrong, not the data.

Why the dirt is planted on purpose:
  Real data is messy. The script deliberately plants 15 orphan HCPs,
  10 duplicates, 8 blank amounts and 5 future dates, so your DQ checks
  in Phase 1 / 2 / 3 have something real to catch. Clean data would
  prove nothing.

WHY A GENERATOR, NOT OPEN-SOURCE DATA OR AN API? (decided 23 Nov 2026)
  Generator = a controlled test. You know the input exactly, so you
  know the output exactly: 800 in, 762 Silver, 38 quarantined.
  If you get 750, your Silver logic is wrong. No other explanation.
  Open-source data = uncontrolled input. CMS Open Payments, the best
  real option, is payments to doctors, not prescriptions: no qty,
  no amount per prescription line, no sales by territory, no
  engagement-then-prescription link, no territory change on 2026-07-01.
  You would have to force the business questions onto data that does
  not contain them. Synthea is synthetic patients, but too clean,
  no dirt, wrong shape for pharma sales. DE-SynPUF is synthetic
  Medicare claims from 2008-2010, old, no engagements.
  API = the same problems, plus non-determinism. An API can paginate,
  rate-limit, change schema, or return different rows next week.
  Run your pipeline twice, get two different counts, and you cannot
  tell if the bug is in your code or the source changed. You are also
  debugging ingestion AND transforms at the same time, instead of
  one at a time.
  So the order is deliberate: generator first, so you learn transforms
  against known answers. Real data second, as a SECOND Bronze source —
  Appendix A: CMS Open Payments, 1 year + 1 state (Alaska, 9,873 rows
  in 2024), only after the core reconciles at 762. An API version
  belongs there, as a Phase 3 stretch. It must not replace this generator.

How to run it (from the repo root):
  python3 shared/scripts/generate_data.py
  wc -l shared/data/raw/*.csv
  Expected: engagements 401, hcp 61, prescriptions 801,
            products 13, territory_map 14  (rows + 1 header line each)
"""

# --- Imports: only Python's standard library, nothing to pip install ---
import csv  # WHY: writes rows to .csv files correctly (quotes, commas, newlines).
            #     Writing CSVs by hand with f-strings breaks when a value contains a comma.
import random  # WHY: picks random specialties, territories, HCPs, amounts, etc.
               #      Without it every row would be identical and useless for testing.
from pathlib import Path  # WHY: builds file paths in a way that works on Windows / Mac / Linux.
                          #      "shared/data/raw" as a plain string would break on Windows backslashes.
from datetime import date, timedelta  # WHY: date = a calendar date (2026-01-01).
                                      #      timedelta = "add N days to a date", used to make rx_date.

# WHY seed 42: random.seed() fixes the random sequence. Run it 10 times,
# you get the exact same 5 files every time. That is why the counts
# (762 Silver, 38 quarantine) are reproducible, and why you must NOT
# change the seed — a different seed gives different random rows and
# the expected counts in the guide stop matching.
random.seed(42)

# WHY this OUT line, and why it looks complicated:
#   __file__ = this script's own location: .../shared/scripts/generate_data.py
#   .resolve() = turn it into a full absolute path, resolving any symlinks.
#   .parent = .../shared/scripts  ->  .parent again = .../shared
#   / "data" / "raw" = .../shared/data/raw
# So OUT is anchored to WHERE THE SCRIPT LIVES, not where you run it from.
# The old line OUT = Path("data/raw") was relative to your terminal's
# current folder — run it from the wrong folder and the CSVs landed
# somewhere else and shared/data/raw/ stayed empty.
OUT = Path(__file__).resolve().parent.parent / "data" / "raw"

# WHY mkdir(parents=True, exist_ok=True):
#   Creates shared/data/raw/ if it does not exist yet.
#   parents=True  = create missing parent folders too (shared/data/ if needed).
#   exist_ok=True = do NOT crash if the folder already exists on a re-run.
OUT.mkdir(parents=True, exist_ok=True)

# --- HCPs: 60 rows ---
# WHY this list comprehension: builds ["T01", "T02", ..., "T10"] in one line.
#   range(1, 11) = numbers 1 to 10 (range stops BEFORE 11, so 1..10).
#   str(i).zfill(2) = pad to 2 digits: 1 -> "01", 10 -> "10". Fixed width
#   matters: "T02" sorts and joins cleanly; "T2" vs "T10" would sort wrong.
#   f"T{...}" = f-string, inserts the padded number after "T".
territories = [f"T{str(i).zfill(2)}" for i in range(1, 11)]

# WHY a fixed list of 5 specialties: HCPs need a specialty column for the
# Gold dimension, and 5 values is enough variety without inventing 60
# different ones. random.choice() below picks one per HCP.
specialties = ["Cardiology", "Oncology", "Neurology", "Endocrinology", "Pulmonology"]

# WHY open(..., "w", newline=""):
#   "w" = write mode, creates / overwrites hcp.csv.
#   newline="" = required by the csv module. Without it, Windows writes
#   a blank line after every row. OUT / "hcp.csv" = shared/data/raw/hcp.csv.
#   "as f" = f is the open file object; it auto-closes when the block ends.
with open(OUT / "hcp.csv", "w", newline="") as f:
    # WHY csv.writer(f): a writer object that turns a Python list into
    # one CSV line, handling quotes and commas for you.
    w = csv.writer(f)
    # WHY this header row first: column names must match the Bronze table
    # in Snowflake / Databricks exactly (hcp_id, name, specialty, ...).
    # If a name is misspelt here, the COPY INTO / read in Phase 1 fails.
    w.writerow(["hcp_id", "name", "specialty", "territory_id", "start_date"])
    # WHY range(1, 61): 60 HCPs, i = 1..60. range stops before 61.
    for i in range(1, 61):
        # WHY each value in this row:
        #   f"HCP{str(i).zfill(3)}" = HCP001, HCP002, ... HCP060. Fixed 3-digit
        #     width, so joins on hcp_id work and sorting is correct.
        #   f"Dr. HCP {i}" = fake name. Synthetic only — never a real doctor.
        #   random.choice(specialties) = give each HCP a random specialty.
        #   random.choice(territories) = give each HCP a random territory T01..T10.
        #   "2024-01-15" = fixed start date, before 2026, so every HCP is
        #     already active when the 2026 prescriptions start.
        w.writerow([f"HCP{str(i).zfill(3)}", f"Dr. HCP {i}", random.choice(specialties),
                    random.choice(territories), "2024-01-15"])

# --- Products: 12 rows ---
# WHY a list comprehension again: builds all 12 product rows in memory first.
#   f"P{str(i).zfill(2)}" = P01..P12, same fixed-width reason as HCPs.
#   f"Product-{chr(64+i)}" = chr(65)="A", chr(66)="B"... so Product-A..Product-L.
#     chr() turns a number into its ASCII letter; 64+1=65="A".
#   random.choice(["Cardio", "Onco", "Neuro"]) = product category.
#   100 + i * 37 = list price: P01=137, P02=174... Deterministic (not random),
#     so the price is easy to check by hand and reproducible with seed 42.
#   range(1, 13) = i = 1..12.
products = [(f"P{str(i).zfill(2)}", f"Product-{chr(64+i)}", random.choice(["Cardio", "Onco", "Neuro"]), 100 + i * 37) for i in range(1, 13)]
with open(OUT / "products.csv", "w", newline="") as f:  # WHY: same "w" + newline="" reason as hcp.csv.
    w = csv.writer(f)  # WHY: same writer reason as above.
    w.writerow(["product_id", "product_name", "category", "list_price"])  # WHY: header must match Bronze PRODUCTS columns.
    # WHY writerows (plural) here, writerow (singular) above: writerows writes
    # the whole list at once. The products list was already built above, so
    # there is no per-row loop needed. Same result, fewer lines.
    w.writerows(products)

# --- Territory map: 3 territories move region on 2026-07-01 ---
with open(OUT / "territory_map.csv", "w", newline="") as f:  # WHY: same file-open reason as above.
    w = csv.writer(f)  # WHY: same writer reason as above.
    w.writerow(["territory_id", "region", "effective_from", "effective_to"])  # WHY: header must match Bronze TERRITORY_MAP columns. effective_from/to are the dates a region applies — this is what makes the date-range JOIN necessary in Gold.
    # WHY loop over the 10 territories: each territory needs at least one
    # mapping row saying which region it belonged to, and when.
    for t in territories:
        # WHY if t in ("T03", "T05", "T07"): these 3 territories are the
        # business problem — they CHANGE region mid-year. That is the whole
        # point of the project: "which region applies?" depends on the date.
        if t in ("T03", "T05", "T07"):
            # WHY two rows for these 3: Row 1 = North, 1 Jan – 30 Jun 2026.
            # Row 2 = West, 1 Jul – 31 Dec 2026. A prescription on 2026-03-01
            # in T03 is North; the same territory on 2026-09-01 is West.
            # An equality JOIN (territory_id only) would get this wrong.
            w.writerow([t, "North", "2026-01-01", "2026-06-30"])
            w.writerow([t, "West", "2026-07-01", "2026-12-31"])
        else:
            # WHY one row for the other 7: they never change region, so one
            # row covering the whole year (2026-01-01 to 2026-12-31) is enough.
            # random.choice(["North", "South", "East"]) = give them a region
            # so all four regions appear in the data (West only comes from
            # the 3 movers after July).
            w.writerow([t, random.choice(["North", "South", "East"]), "2026-01-01", "2026-12-31"])

# --- Prescriptions: ~800 rows + planted dirt ---
# WHY start = date(2026, 1, 1): every prescription is in 2026. The business
# question is "2026 sales by month", so the data year is 2026.
start = date(2026, 1, 1)
# WHY rows = [] first, then fill it, then plant dirt, then write it:
# The dirt (orphans, duplicates, blanks, future dates) is planted by
# EDITING rows after they are generated. You cannot edit rows you have
# already written to the file, so they are collected in a list first.
rows = []
# WHY range(1, 801): 800 prescriptions, i = 1..800.
for i in range(1, 801):
    # WHY random.randint(0, 316) and why 316, not 365:
    #   start + 316 days = 2026-11-13. Normal dates are CAPPED at 13 Nov 2026.
    #   The guide was written around "today" ~13 Nov 2026. If normal dates
    #   ran to 27 Nov or 31 Dec, 18 legitimate prescriptions would be dated
    #   AFTER today and your Silver future-date rule would quarantine them
    #   by mistake — Silver would be 744, not 762. The cap is a fix, not a typo.
    rx_date = start + timedelta(days=random.randint(0, 316))  # capped at 2026-11-13: later dates would be "future" vs CURRENT_DATE() and get quarantined by mistake
    # WHY each value in this row (index matters — the dirt loops below use indexes):
    #   [0] f"RX{str(i).zfill(4)}" = RX0001..RX0800, the stable key for dedupe.
    #   [1] random HCP 1..60 = which doctor prescribed. HCP001..HCP060 only.
    #   [2] random product P01..P12.
    #   [3] rx_date.isoformat() = "2026-03-14" as text. CSVs store text, not
    #       Python dates, so .isoformat() converts it to YYYY-MM-DD text.
    #   [4] random.randint(1, 10) = quantity, 1 to 10 units.
    #   [5] round(random.uniform(500, 5000), 2) = amount Rs 500–5000, rounded
    #       to 2 decimals like real money.
    #   [6] (rx_date + 1 day).isoformat() = updated_at, one day after rx_date.
    #       WHY: dedupe keeps the row with the LATEST updated_at per rx_id,
    #       so updated_at must exist and be meaningful, not random.
    rows.append([f"RX{str(i).zfill(4)}", f"HCP{str(random.randint(1, 60)).zfill(3)}",
                 f"P{str(random.randint(1, 12)).zfill(2)}", rx_date.isoformat(),
                 random.randint(1, 10), round(random.uniform(500, 5000), 2),
                 (rx_date + timedelta(days=1)).isoformat()])

# Planted dirt: 15 orphans, 10 duplicates, 8 NULL amounts, 5 future dates
# WHY plant dirt at fixed indexes (rows 0-37): so the counts are exact and
# reproducible. Random dirt would give a different quarantine count every run.
for i in range(15):  # WHY range(15) = rows 0..14, the first 15 rows.
    # WHY rows[i][1] = HCP900..HCP914: [1] is the hcp_id column. HCP900+
    # does NOT exist in hcp.csv (which only has HCP001..HCP060), so these
    # 15 rows are ORPHANS — prescriptions pointing at a doctor who does not exist.
    rows[i][1] = f"HCP9{str(i).zfill(2)}"          # no such HCP
for i in range(15, 25):  # WHY range(15, 25) = rows 15..24, the next 10 rows.
    # WHY rows[i] = rows[i - 15].copy(): copy rows 0..14 over rows 15..24.
    # That DUPLICATES 10 rx_ids (RX0001..RX0010 appear twice). .copy() is
    # essential: without it both list entries would point to the SAME list
    # object, and editing one later would edit the other.
    # WHY this matters for the maths: the 10 duplicates are copies of
    # ORPHAN rows, so they are already orphans. Orphan total = 15 + 10 = 25,
    # and dedupe removes 0 additional clean rows. 800 - 8 - 5 - 25 = 762.
    rows[i] = rows[i - 15].copy()                  # duplicate rx_id
for i in range(25, 33):  # WHY range(25, 33) = rows 25..32, 8 rows.
    # WHY rows[i][5] = "": [5] is the amount column. "" = blank in the CSV,
    # which Snowflake loads as NULL (NULL_IF = ('', 'NULL')). Your Silver
    # rule must check AMOUNT IS NULL, not AMOUNT = ''. 8 rows, not random.
    rows[i][5] = ""                                # NULL amount
for i in range(33, 38):  # WHY range(33, 38) = rows 33..37, 5 rows.
    # WHY rows[i][3] = "2027-03-01": [3] is the rx_date column. 2027-03-01
    # is in the FUTURE, so Silver must quarantine it (rx_date > CURRENT_DATE()).
    # All 5 use the same date so you can find them with one query.
    rows[i][3] = "2027-03-01"                      # future date
with open(OUT / "prescriptions.csv", "w", newline="") as f:  # WHY: same file-open reason as above.
    w = csv.writer(f)  # WHY: same writer reason as above.
    w.writerow(["rx_id", "hcp_id", "product_id", "rx_date", "qty", "amount", "updated_at"])  # WHY: header must match Bronze PRESCRIPTIONS columns, in this order — the dirt loops above rely on these positions.
    # WHY writerows(rows): writes all 800 rows (clean + dirt) at once.
    w.writerows(rows)

# --- Engagements: ~400 rows ---
with open(OUT / "engagements.csv", "w", newline="") as f:  # WHY: same file-open reason as above.
    w = csv.writer(f)  # WHY: same writer reason as above.
    w.writerow(["engagement_id", "hcp_id", "rep_id", "engagement_date", "channel", "duration_min"])  # WHY: header must match Bronze ENGAGEMENTS columns.
    # WHY range(1, 401): 400 engagements, i = 1..400.
    for i in range(1, 401):
        # WHY each value:
        #   f"ENG{str(i).zfill(4)}" = ENG0001..ENG0400, the engagement key.
        #   random HCP 1..60 = who was engaged. Note: NO dirt here — engagements
        #     are clean, so the 30-day lift logic in Gold is tested on clean data.
        #   f"REP{str(random.randint(1, 8)).zfill(2)}" = REP01..REP08, 8 sales reps.
        #   engagement_date = same 0–316 day cap as prescriptions (2026-11-13),
        #     so engagements are also never "in the future" by accident.
        #   random.choice(["visit", "call", "email"]) = how the engagement happened.
        #   random.randint(5, 60) = duration in minutes, 5 to 60.
        w.writerow([f"ENG{str(i).zfill(4)}", f"HCP{str(random.randint(1, 60)).zfill(3)}",
                    f"REP{str(random.randint(1, 8)).zfill(2)}",
                    (start + timedelta(days=random.randint(0, 316))).isoformat(),  # same 2026-11-13 cap as prescriptions
                    random.choice(["visit", "call", "email"]), random.randint(5, 60)])

# WHY this print: proof the script actually ran. If you see "Done." and the
# 5 filenames, the files exist. If you do not, the script crashed before here.
print("Done. Files in shared/data/raw/:")
# WHY sorted(OUT.glob("*.csv")): glob finds every .csv in shared/data/raw/,
# sorted() lists them alphabetically (engagements, hcp, prescriptions,
# products, territory_map) so the output is the same every run.
# p.name = just the filename, not the full path — easier to read.
for p in sorted(OUT.glob("*.csv")):
    print(" ", p.name)

# --- After running, check yourself (do not skip this) ---
# wc -l shared/data/raw/*.csv
#   Expected: engagements 401, hcp 61, prescriptions 801, products 13, territory_map 14
#   (each = data rows + 1 header line)
# Then, in Snowflake / Databricks, check the dirt is there:
#   Orphan HCPs:  SELECT COUNT(*) FROM bronze.prescriptions WHERE hcp_id LIKE 'HCP9%';  -- expect 25
#   Blank amounts: SELECT COUNT(*) FROM bronze.prescriptions WHERE amount IS NULL;      -- expect 8
#   Future dates:  SELECT COUNT(*) FROM bronze.prescriptions WHERE rx_date > '2026-11-13'; -- expect 5
#   Duplicates:    SELECT rx_id, COUNT(*) c FROM bronze.prescriptions GROUP BY 1 HAVING c > 1; -- expect 10 rx_ids
# If those 4 checks pass, your data is correct and Silver must be 762.
