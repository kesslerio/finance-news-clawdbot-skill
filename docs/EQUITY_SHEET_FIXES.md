# Equity Sheet Fixes

## NRR Column (Column Q) - Range Values Fix

**Problem:** Values like "115-120%", "125%+", "N/A" in NRR column cause #VALUE! errors in MSS Score formula (columns Y/Z).

**Root cause:** Excel/Sheets formulas cannot perform math operations on text ranges.

**Solution:** Convert all NRR values to single numeric percentages.

### Conversion Rules

**Standard formats:**

| Original | Fixed | Calculation | Rationale |
|----------|-------|-------------|-----------|
| 115-120% | 117.5% | (115+120)/2 | Midpoint (conservative estimate) |
| 120-125% | 122.5% | (120+125)/2 | Midpoint |
| 125%+ | 125% | Use lower bound | Conservative (actual may be higher) |
| N/A | [blank] | Leave empty | MSS formula uses IFERROR to handle blanks |
| 110% | 110% | Already valid | No change needed |

**Edge cases (normalize before converting):**

| Variant | Normalized | Notes |
|---------|------------|-------|
| 115–120% (en-dash) | 115-120% | Replace en-dash with hyphen |
| 115 - 120% (spaces) | 115-120% | Remove spaces around hyphen |
| >=125% | 125%+ | Convert to standard "+" format |
| 125%+ or higher | 125%+ | Strip extra text |

### Fix Procedure

**Option A: Manual fix via browser**
1. Open sheet: https://docs.google.com/spreadsheets/d/1lTpdbDjqW40qe4YUvk_1vBzKYLUNrmLZYyQN-7HmFJg/edit#gid=0
2. **IMPORTANT:** Select column Q header → Format → Number → Percent
   - This ensures values are stored as numbers, not text
   - If column is set to "Plain text", entering "117.5%" stores as text → still causes errors
3. Navigate to column Q (NRR)
4. For each range value:
   - Calculate midpoint (e.g., (115+120)/2 = 117.5)
   - Replace with single percentage: `117.5%`
   - Sheets auto-converts to numeric percentage when column is formatted correctly
5. For "N/A" → delete content (leave blank)
6. For "125%+" → replace with `125%`
7. **Verify:** After editing, click cell → formula bar should show `1.175` (not `"117.5%"` with quotes)

**Option B: Sheets API fix (requires Sheets API enabled)**
```bash
# Enable Sheets API first:
# https://console.developers.google.com/apis/api/sheets.googleapis.com/overview?project=831892255935

# Then use gog CLI with USER_ENTERED mode (important!)
gog-shapescale --account martin@shapescale.com sheets update \
  1lTpdbDjqW40qe4YUvk_1vBzKYLUNrmLZYyQN-7HmFJg \
  'Equity!Q5' '117.5%'

# Note: By default, gog CLI uses USER_ENTERED input mode, which:
# - Parses "117.5%" as numeric percentage (0.1175 internally)
# - If it used RAW mode instead, "117.5%" would store as text → still causes errors
# - Verify after writing: cell should show numeric percentage, not text with quotes
```

### Impact

Fixing NRR ranges will:
- ✅ Eliminate #VALUE! errors in MSS Score column (Y)
- ✅ Eliminate #VALUE! errors in MSS Rating column (Z)
- ✅ Allow proper numerical analysis and sorting
- ✅ Make formulas copyable to new rows without errors

### How MSS Formula Handles Blank NRR Values

The MSS Score formula (column Y) includes `IFERROR()` wrapper to handle missing data:
- **Blank NRR cell** → Formula treats as missing data, uses available metrics only
- **Not treated as 0%** → Blank is excluded from calculation (doesn't penalize score)
- **Better than text "N/A"** → Text causes #VALUE! error, blank is handled gracefully

**Example:** If NRR is blank but other metrics exist (Rev Growth, Rule of 40, etc.), MSS Score calculates using remaining metrics without error.

### Related Columns

Other columns that need single numeric values (not ranges):
- **Column M (Rule of 40 Ops)**: Should be calculated value (Ops Margin + Rev Growth)
- **Column O (Rule of 40 FCF)**: Should be calculated value (FCF Margin + Rev Growth)
- Both can be negative for pre-profitable/turnaround companies

### Prevention

When adding new companies:
1. Always use single percentage values in NRR column
2. Test MSS Score formula immediately after adding row
3. If #VALUE! error appears → check Q column for ranges/text
