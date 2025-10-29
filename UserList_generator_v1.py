from __future__ import annotations
"""
Rotman International Trading Competition (RITC) User List Generator
Rotman BMO Finance Research and Trading Lab, Uniersity of Toronto (C)
All rights reserved.
"""

"""
User Generator
--------------
Generates login rosters for teams.

Default behavior:
- If no names file is provided, output only: TraderID, Password
- If a names file (CSV/XLSX) is provided, output: TraderID, First Name, Last Name, Password

Rules:
- TeamID: 4-character alphanumeric code, must start with a letter, unique per team
- TraderID: "{TEAMID}-{i}" (i starts at 1 for each team)
- Password: simple lowercase word; same for all members in a team

CLI examples:
  python UserList_generator.py --teams 10 --size 2 --out userlist.xlsx
  python UserList_generator.py --teams 10 --size 2 --names participants.xlsx --out userlist.xlsx
  python UserList_generator.py --teams 10 --size 2 --out userlist.csv --autofill-names --seed 123  # (optional)
"""


import argparse
import hashlib
import random
import string
from pathlib import Path
from typing import Optional, List

import pandas as pd

# Simple, lowercase dictionary for passwords (no caps/symbols/spaces)
_SIMPLE_WORDS = [
    "water", "bear", "cloudy", "rain", "windy", "wave", "spark", "loud", "tide", "earth",
    "apple", "dream", "stone", "river", "sun", "moon", "forest", "ocean", "sand", "leaf",
    "fire", "cloud", "tree", "field", "plain", "hill", "breeze", "storm", "snow", "rainy"
]


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename headers to 'First Name' and 'Last Name' if they look like first/last."""
    colmap = {}
    for c in df.columns:
        lc = str(c).strip().lower()
        if lc in {"first", "first name", "firstname", "given", "given name"}:
            colmap[c] = "First Name"
        elif lc in {"last", "last name", "lastname", "family", "surname"}:
            colmap[c] = "Last Name"

    if "First Name" not in colmap.values() or "Last Name" not in colmap.values():
        raise ValueError("Names file must have two columns for first and last names (any reasonable spelling).")

    return df.rename(columns=colmap)[["First Name", "Last Name"]]


def _read_names(names_path: str | Path) -> pd.DataFrame:
    p = Path(names_path)
    if not p.exists():
        raise FileNotFoundError(f"Names file not found: {p}")
    if p.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(p)
    else:
        df = pd.read_csv(p)
    return _normalize_columns(df)


def _hash_to_alpha_num(h: str) -> str:
    """Map hex string to an A–Z0–9 string; first char guaranteed to be a letter."""
    letters = string.ascii_uppercase
    digits = "0123456789"
    idx0 = int(h[:2], 16) % len(letters)  # first must be a letter
    s = letters[idx0]
    pool = letters + digits
    for i in range(2, 8, 2):
        s += pool[int(h[i:i + 2], 16) % len(pool)]
    return s


def _make_team_id(seed_text: str, used: set[str]) -> str:
    """Deterministically create a unique 4-char TeamID that starts with a letter."""
    counter = 0
    while True:
        base_hash = hashlib.md5((seed_text + f"#{counter}").encode()).hexdigest()
        code = _hash_to_alpha_num(base_hash)[:4]
        if code not in used and code[0].isalpha():
            used.add(code)
            return code
        counter += 1


def _password_for_team(seed_text: str) -> str:
    """Deterministically choose a simple lowercase word based on team seed."""
    h = int(hashlib.sha1(seed_text.encode()).hexdigest(), 16)
    return _SIMPLE_WORDS[h % len(_SIMPLE_WORDS)]


def _autofill_names(n: int, rng: random.Random) -> pd.DataFrame:
    """Create placeholder names if user opts in."""
    firsts = [
        "Alex", "Jamie", "Taylor", "Jordan", "Casey", "Riley", "Avery", "Morgan", "Charlie", "Sam",
        "Quinn", "Rowan", "Eden", "Kai", "Remy", "Skye", "Noah", "Liam", "Emma", "Olivia",
        "Ethan", "Mia", "Ava", "Isla", "Leo", "Zoe", "Maya", "Ivy", "Mila"
    ]
    lasts = [
        "Chen", "Wang", "Singh", "Gupta", "Patel", "Brown", "Davis", "Garcia", "Rodriguez", "Martinez",
        "Hernandez", "Kim", "Park", "Nguyen", "Tran", "Khan", "Hsu", "Liu", "Zhang", "Ma", "Li", "Cui", "Gao"
    ]
    rows = [(rng.choice(firsts), rng.choice(lasts)) for _ in range(n)]
    return pd.DataFrame(rows, columns=["First Name", "Last Name"])


def generate_users(
    n_teams: int,
    team_size: int,
    names_path: Optional[str] = None,
    out_path: str = "users.csv",
    seed: Optional[int] = None,
    autofill_names: bool = False
) -> pd.DataFrame:
    """
    Generate the roster and write it to CSV/Excel based on `out_path` extension.

    - If `names_path` is None and `autofill_names` is False:
        Output columns = TraderID, Password
    - If `names_path` is provided (or autofill_names is True):
        Output columns = TraderID, First Name, Last Name, Password
    """
    if n_teams <= 0 or team_size <= 0:
        raise ValueError("n_teams and team_size must be positive integers.")

    rng = random.Random(seed)
    total = n_teams * team_size

    have_names = False
    if names_path:
        df_names = _read_names(names_path)
        if len(df_names) < total:
            raise ValueError(f"Names file has {len(df_names)} rows but needs at least {total}.")
        df_names = df_names.iloc[:total].reset_index(drop=True)
        have_names = True
    elif autofill_names:
        df_names = _autofill_names(total, rng)
        have_names = True
    else:
        df_names = None  # no names case

    used_team_ids: set[str] = set()
    out_rows: List[list] = []

    for t in range(n_teams):
        # Build a deterministic seed text (with or without names)
        if have_names:
            block = df_names.iloc[t * team_size : (t + 1) * team_size]
            seed_text = "|".join(f"{r['First Name']} {r['Last Name']}" for _, r in block.iterrows())
        else:
            seed_text = f"team#{t}-size{team_size}"

        team_id = _make_team_id(seed_text, used_team_ids)
        password = _password_for_team(seed_text)

        for i in range(1, team_size + 1):
            trader_id = f"{team_id}-{i}"
            if have_names:
                fn = str(df_names.iloc[t * team_size + (i - 1)]["First Name"])
                ln = str(df_names.iloc[t * team_size + (i - 1)]["Last Name"])
                out_rows.append([trader_id, password, fn, ln])
            else:
                out_rows.append([trader_id, password])

    # Build DataFrame with correct columns
    if have_names:
        out_df = pd.DataFrame(out_rows, columns=["TraderID", "Password", "First Name", "Last Name"])
    else:
        out_df = pd.DataFrame(out_rows, columns=["TraderID", "Password"])

    # Save file based on extension
    out_path = str(out_path)
    if out_path.lower().endswith(".xlsx"):
        out_df.to_excel(out_path, index=False)  # requires openpyxl
    else:
        out_df.to_csv(out_path, index=False)

    return out_df


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate user roster for teams.")
    p.add_argument("--teams", type=int, required=True, help="Number of teams")
    p.add_argument("--size", type=int, required=True, help="Members per team")
    p.add_argument("--names", type=str, default=None,
                   help="Optional CSV/XLSX with two columns (First/Last names). Grouped in blocks of --size.")
    p.add_argument("--out", type=str, default="users.csv",
                   help="Output path (.csv or .xlsx). Extension selects the format.")
    p.add_argument("--seed", type=int, default=None, help="Optional seed for reproducibility")
    p.add_argument("--autofill-names", action="store_true",
                   help="If no names file is provided, generate placeholder names (optional).")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    df = generate_users(
        n_teams=args.teams,
        team_size=args.size,
        names_path=args.names,
        out_path=args.out,
        seed=args.seed,
        autofill_names=args.autofill_names
    )
    print(f"Saved {len(df)} rows to {args.out}")
