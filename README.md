# User List Generator for RITC Competition

Generate a clean roster for trading competitions or labs.

**Outputs** a table with either:

* **Without names file:** `TraderID, Password`
* **With names file (CSV/XLSX):** `TraderID, First Name, Last Name, Password`

`TraderID` is constructed as `TEAMID-#` (e.g., `A1BC-1`, `A1BC-2`).
`TEAMID` is a 4-character code that **starts with a letter** and is **unique per team**.
Teammates share the **same simple lowercase password** (no caps/symbols).

---

## Features

* 🔢 **Configurable team counts and team sizes**
* 📄 **Optional names file** (CSV/XLSX) using flexible header spellings for first/last name
* 🔐 **Simple, human-typeable passwords** (e.g., `water`, `cloudy`, `wave`)
* 🧮 **Deterministic** TeamIDs and passwords from the input + optional `--seed`
* 💾 **Saves as CSV or Excel** depending on output filename extension
* 🧰 **CLI and Python API**

---

## Output Schema

When **no names file** is provided:

```
TraderID, Password
```

When a **names file** is provided (or when `--autofill-names` is used):

```
TraderID, First Name, Last Name, Password
```

* `TraderID`: `{TEAMID}-{i}` where `i` = 1..team_size
* `TEAMID`: 4 chars, `[A-Z][A-Z0-9]{3}`, unique across teams
* `Password`: lowercase word; same for everyone on the team

---

## TeamID & Password Rules

* **TeamID**

  * 4 characters total
  * **First character is always a letter** (`A–Z`)
  * Remaining characters are drawn from `A–Z0–9`
  * Deterministic and **unique per team**

* **Password**

  * Lowercase word (no capitals, spaces, or special characters)
  * Same password for all members on a team
  * Deterministic given the same inputs/seed

---

## Installation

> Python 3.8+ is fine. On Windows with Python 3.13 you’ll likely need to install dependencies.

**Option A — Virtual environment (recommended)**

```bat
py -3.13 -m venv .venv
.\.venv\Scripts\activate

py -m ensurepip --upgrade
py -m pip install --upgrade pip setuptools wheel
py -m pip install "pandas>=2.2" "openpyxl>=3.1"
```

**Option B — Conda (good if wheels for your Python version are lagging)**

```bat
conda create -n usergen python=3.12 pandas openpyxl -y
conda activate usergen
```

---

## Quick Start (CLI)

> Replace the script name below with your file name (e.g., `UserList_generator.py`).

* **No names file → only `TraderID, Password` (Excel)**:

```bash
python UserList_generator.py --teams 12 --size 2 --out users.xlsx
```

* **With names file → includes first/last names**:

```bash
python UserList_generator.py --teams 12 --size 2 --names participants.xlsx --out users.xlsx
```

* **Optional:** generate placeholder names (no file):

```bash
python UserList_generator.py --teams 12 --size 2 --out users.xlsx --autofill-names --seed 42
```

**CLI Flags**

```
--teams            Number of teams (required)
--size             Team size / members per team (required)
--names            Optional CSV/XLSX file with names
--out              Output path (.csv or .xlsx). Default: users.csv
--seed             Optional integer for reproducibility
--autofill-names   Generate placeholder names if no file is provided
```

---

## Names File Format

* **Two columns** for names; flexible header spellings accepted:

  * First name column may be `First`, `First Name`, `Firstname`, `Given`, `Given Name`
  * Last name column may be `Last`, `Last Name`, `Lastname`, `Family`, `Surname`
* **Grouping into teams:** rows are grouped in **blocks of `--size`** in the **given order**.

  * Example: if `--size 4`, then rows 1–4 are Team 1, rows 5–8 are Team 2, etc.

**CSV/Xslx example**

```csv
First Name,Last Name
Elizabeth,Hsu
Isaac,Jung
Po-Tsun,Chen
Zian,Chen
```

**Excel** works the same way; the sheet’s first row should contain headers.

---

## Python API

```python
from UserList_generator import generate_users

# 1) No names file -> only TraderID + Password; writes Excel
df = generate_users(
    n_teams=12,
    team_size=2,
    names_path=None,
    out_path="users.xlsx",  # .xlsx -> Excel; .csv -> CSV
    seed=42,
    autofill_names=False
)

# 2) With names file -> includes names
df2 = generate_users(
    n_teams=12,
    team_size=2,
    names_path="participants.xlsx",
    out_path="users.xlsx",
    seed=42
)

# 3) No file but include placeholder names (optional)
df3 = generate_users(
    n_teams=12,
    team_size=2,
    names_path=None,
    out_path="users.xlsx",
    seed=42,
    autofill_names=True
)
```

---

## Examples

**No names file (Excel):**

```bash
python UserList_generator.py --teams 6 --size 2 --out users.xlsx
```

Output columns:

```
| TraderID | Password |
| -------- | -------- |
| A1BC-1   | water    |
| A1BC-2   | water    |
| J9Q0-1   | cloud    |
| J9Q0-2   | cloud    |
| KP0P-1   | tide     |
| KP0P-2   | tide     |

...
```

**With names file (CSV):**

```bash
python UserList_generator.py --teams 6 --size 2 --names participants.csv --out users.csv
```

Output columns:

```
| TraderID | First Name | Last Name | Password |
| -------- | ---------- | --------- | -------- |
| T005-1   | Elizabeth  | Hsu       | water    |
| T005-2   | Isaac      | Jung      | water    |
| X125-1   | Po-Tsun    | Chen      | bear     |
| X125-2   | Zian       | Chen      | bear     |
| DEG6-1   | Rohan      | Kapoor    | cloudy   |
| DEG6-2   | Palash     | Shah      | cloudy   |

...
```

---

## Determinism & Reproducibility

* Results are deterministic for the **same inputs** (same names file/order, same `--teams`, `--size`) and **same `--seed`** (if used).
* Changing the **order** of the names in your file changes team grouping and therefore TeamIDs/passwords.

---

## Troubleshooting

* **`ModuleNotFoundError: No module named 'pandas'`**
  Install dependencies:

  ```bat
  py -m pip install pandas
  ```
* **Writing `.xlsx` fails**
  Install `openpyxl`:

  ```bat
  py -m pip install openpyxl
  ```
* **“the following arguments are required: --teams, --size”**
  You must pass both flags:

  ```bash
  python UserList_generator.py --teams 12 --size 2 --out users.xlsx
  ```
* **Python 3.13 wheel gaps**
  If you can’t install wheels for your exact Python version, use a **venv** with a slightly older Python (3.12) via Conda, or wait for wheels to publish.

---

## Customization

* **Password wordlist:** edit `_SIMPLE_WORDS` in the script.
* **TeamID length/rules:** adjust `_hash_to_alpha_num` and `_make_team_id`.
* **Column names:** modify the `normalize` mapping or output column list where the DataFrame is constructed.

---

## Security Note

This tool is intended for **classroom/competition** use with **simple** passwords for ease of distribution. For production systems, use stronger passwords and secure credential distribution.

---

## License
MIT License
