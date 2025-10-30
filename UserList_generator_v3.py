#!/usr/bin/env python3
"""
UserList_generator.py (v4)

Changes:
- TraderList columns: TraderID, First Name, Last Name, Password (Password in column D)
- TeamList   columns: TeamID,  First Name, Last Name, Password (Password in column D)
  * TeamList is de-duplicated: ONE row per TeamID (names left blank)
- Admin accounts: create FRTL-1, FRTL-2, ... with distinct passwords
  * --admin-count N (default 0), --admin-prefix FRTL (default)
  * Appended to TraderList; TeamList includes one row for the admin TeamID

Outputs:
  1) --out   (TraderList)
  2) --out2  (TeamList)
  3) --out3  (RegistrationList)  [unchanged format]

Usage (example):
  python UserList_generator_v3.py --names BU_MSMFT_TeamList.xlsx --team-col "Team" --first-col "First Name" --last-col "Last Name" --email-col "BU Email" --out TraderList.xlsx --out2 TeamList.xlsx --out3 RegistrationList.xlsx --admin-count 2 --admin-prefix FRTL
"""

from __future__ import annotations

import argparse
import hashlib
import pandas as pd
from typing import Optional, List, Tuple, Dict
import random

# ---------- IO helpers ----------
def _read_excel_any(path: str, sheet: Optional[str], all_sheets: bool) -> pd.DataFrame:
    if all_sheets:
        sheets = pd.read_excel(path, sheet_name=None)
        dfs = []
        for name, df in sheets.items():
            if df is None or df.empty:
                continue
            df["__sheet__"] = str(name)
            dfs.append(df)
        if not dfs:
            raise ValueError("No non-empty worksheets found.")
        return pd.concat(dfs, ignore_index=True)
    if sheet:
        return pd.read_excel(path, sheet_name=sheet)
    return pd.read_excel(path)

def _read_names(path: str, sheet: Optional[str], all_sheets: bool) -> pd.DataFrame:
    p = path.lower()
    if p.endswith((".xlsx", ".xls")):
        return _read_excel_any(path, sheet=sheet, all_sheets=all_sheets)
    if p.endswith(".csv"):
        return pd.read_csv(path)
    raise ValueError("Names file must be .xlsx/.xls or .csv")

def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    def norm(c: str) -> str:
        c = str(c).strip().lower().replace("_", " ")
        return " ".join(c.split())
    out = df.copy()
    out.columns = [norm(c) for c in out.columns]
    return out

def _trim_strings(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_object_dtype(out[col]) or pd.api.types.is_string_dtype(out[col]):
            out[col] = out[col].astype("string").fillna("").str.strip()
    return out

def _find_by_keywords(df: pd.DataFrame, keywords: List[str]) -> Optional[str]:
    for kw in keywords:
        for c in df.columns:
            if kw in c:
                return c
    return None

def _resolve_columns(
    df: pd.DataFrame,
    team_col_arg: Optional[str],
    first_col_arg: Optional[str],
    last_col_arg: Optional[str],
    email_col_arg: Optional[str],
) -> Tuple[str, str, str, Optional[str]]:
    def normalize_name(name: str) -> str:
        return " ".join(name.strip().lower().replace("_", " ").split())
    def pick_exact(arg: Optional[str]) -> Optional[str]:
        if not arg:
            return None
        want = normalize_name(arg)
        for c in df.columns:
            if c == want:
                return c
        raise ValueError(f"Column '{arg}' not found. Available columns: {list(df.columns)}")

    col_team  = pick_exact(team_col_arg)
    col_first = pick_exact(first_col_arg)
    col_last  = pick_exact(last_col_arg)
    col_email = pick_exact(email_col_arg)

    if col_first is None:
        col_first = _find_by_keywords(df, ["first name","firstname","first","given"])
    if col_last is None:
        col_last  = _find_by_keywords(df, ["last name","lastname","last","surname","family name","family"])
    if col_team is None:
        col_team  = _find_by_keywords(df, ["teamid","team id","team code","team#","team #","team no","team number","team"])
    if col_email is None:
        col_email = _find_by_keywords(df, ["email","e-mail","mail","bu email","email address"])

    if not (col_team and col_first and col_last):
        raise ValueError(
            "Could not detect Team / First / Last columns.\n"
            f"Columns seen: {list(df.columns)}\n"
            "Tip: pass --team-col, --first-col, --last-col (and optionally --email-col)."
        )
    return col_team, col_first, col_last, col_email

# ---------- ID & password helpers ----------
_BASE36 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

def _to_base36(n: int) -> str:
    if n == 0:
        return "0"
    s = []
    while n > 0:
        n, r = divmod(n, 36)
        s.append(_BASE36[r])
    return "".join(reversed(s))

def _team_code_4(label: str, used: set[str]) -> str:
    """
    Deterministically map arbitrary team label -> 4-char alphanumeric code:
    - starts with a letter
    - unique across teams (resolve collisions by incrementing salt)
    """
    salt = 0
    while True:
        data = f"{label}::{salt}".encode("utf-8", "ignore")
        digest = hashlib.sha1(data).digest()
        n = int.from_bytes(digest, "big")
        code = _to_base36(n).upper()
        code = "".join(ch for ch in code if ch.isalnum())
        if len(code) < 4:
            code = (code + "AAAA")[:4]
        else:
            code = code[:4]
        if not code[0].isalpha():
            salt += 1
            continue
        if code in used:
            salt += 1
            continue
        used.add(code)
        return code

def _password_for_team(seed_text: str) -> str:
    words = ["wave","cloudy","apple","rain","earth","spark","dream","tide","bear","windy","stone", "river", "sun", "moon", "forest", "ocean", "sand", "leaf",
    "fire", "cloud", "tree", "field", "plain", "hill", "breeze", "storm", "snow", "rainy"]
    idx = int(hashlib.sha1(seed_text.encode()).hexdigest(), 16) % len(words)
    return words[idx]

def _password_unique(idx: int) -> str:
    """Different-looking simple password per admin account."""
    words = ["wave","cloudy","apple","rain","earth","spark","dream","tide","bear","windy","stone", "river", "sun", "moon", "forest", "ocean", "sand", "leaf",
    "fire", "cloud", "tree", "field", "plain", "hill", "breeze", "storm", "snow", "rainy"]
    return words[idx % len(words)] + str(100 + (idx % 900))

# ---------- main ----------
def generate_users(
    names_path: str,
    out_path: str,
    out_path_team: str,
    out_path_reg: str,
    team_col_arg: Optional[str],
    first_col_arg: Optional[str],
    last_col_arg: Optional[str],
    email_col_arg: Optional[str],
    sheet: Optional[str],
    all_sheets: bool,
    admin_count: int,
    admin_prefix: str,
    seed: Optional[int] = None,
) -> None:
    random.seed(seed)

    raw = _read_names(names_path, sheet=sheet, all_sheets=all_sheets)
    df = _trim_strings(_normalize_columns(raw))

    col_team, col_first, col_last, col_email = _resolve_columns(
        df, team_col_arg, first_col_arg, last_col_arg, email_col_arg
    )

    # Clean rows: need a team and at least one of first/last
    df = df[(df[col_team].notna()) & ((df[col_first].notna()) | (df[col_last].notna()))].copy()

    # Determine ordered unique team labels → team numbers 1..K
    ordered_labels = []
    seen = set()
    for lbl in df[col_team].astype(str):
        if lbl not in seen:
            seen.add(lbl)
            ordered_labels.append(lbl)
    team_number_map = {lbl: i+1 for i, lbl in enumerate(ordered_labels)}

    # Deterministic 4-char team code per original label
    used_codes: set[str] = set()
    team_code_map: Dict[str, str] = {lbl: _team_code_4(lbl, used_codes) for lbl in ordered_labels}

    # Build outputs
    trader_rows, per_person_team_rows, reg_rows = [], [], []

    REG_COLS = [
        "Team #",
        "Team Name",
        "Team Code",
        "Individual Trader ID",
        "Password",
        "Email Address",
        "First Name",
        "Last Name",
        "Home School / College",
        "Please enter your information - Primary Degree",
        "Please enter your information - Expected Graduation Year",
        "Are you?",
        "Registering for",
    ]

    for orig_team_label, members in df.groupby(col_team, sort=False):
        team_no   = team_number_map[str(orig_team_label)]
        team_code = team_code_map[str(orig_team_label)]
        seed_txt  = "|".join((members[col_first].fillna("") + " " + members[col_last].fillna("")).astype(str))
        password  = _password_for_team(seed_txt if seed_txt else str(team_code))

        for i, (_, r) in enumerate(members.iterrows(), start=1):
            first = str(r.get(col_first, "") or "").strip()
            last  = str(r.get(col_last,  "") or "").strip()
            email = str(r.get(col_email, "") or "").strip() if col_email else ""
            trader_id = f"{team_code}-{i}"

            # 1) TraderList → (TraderID, First, Last, Password)  [Password at column D]
            trader_rows.append([trader_id, first, last, password])

            # For TeamList (we will dedupe later):
            per_person_team_rows.append([team_code, first, last, password])

            # 3) RegistrationList (unchanged)
            reg_rows.append([
                team_no,                    # Team #
                "",                         # Team Name (blank)
                team_code,                  # Team Code
                trader_id,                  # Individual Trader ID
                password,                   # Password
                email,                      # Email Address
                first,                      # First Name
                last,                       # Last Name
                "", "", "", "", ""          # Remaining blanks
            ])

    # ---- Admin accounts ----
    # Add FRTL-1, FRTL-2, ...  with distinct simple passwords; names blank; email blank
    if admin_count > 0:
        admin_team_code = admin_prefix  # also 4-char + starts with letter as per your example
        # Ensure admin team code is not colliding with generated 4-char codes
        if admin_team_code in {c for c in team_code_map.values()}:
            admin_team_code = admin_prefix[:3] + "A"  # small tweak if collision
        # Generate N admin trader IDs
        for i in range(1, admin_count + 1):
            trader_id = f"{admin_team_code}-{i}"
            pwd = _password_unique(i)  # different per admin
            trader_rows.append([trader_id, "", "", pwd])
            per_person_team_rows.append([admin_team_code, "", "", pwd])
            # Registration row (optional; still add for completeness)
            reg_rows.append([
                0, "", admin_team_code, trader_id, pwd, "", "", "", "", "", "", "", ""
            ])

    # DataFrames with required column order (Password in column D)
    df_trader = pd.DataFrame(trader_rows, columns=["TraderID","First Name","Last Name","Password"])

    # ---- TeamList: de-dup by TeamID, keep the FIRST appearing member's name ----
    df_team_people = pd.DataFrame(
        per_person_team_rows, columns=["TeamID", "First Name", "Last Name", "Password"]
    )
    # Keep the first row per TeamID (preserves input order), including names
    df_team = (
        df_team_people
        .groupby("TeamID", sort=False, as_index=False)
        .first()[["TeamID", "First Name", "Last Name", "Password"]]   # ensure Password is col D
    )

    # match requested order: TeamID, First Name, Last Name, Password (with blank names)
    # df_team["First Name"] = ""
    # df_team["Last Name"]  = ""
    df_team = df_team[["TeamID","First Name","Last Name","Password"]]

    # Registration
    df_reg = pd.DataFrame(reg_rows, columns=[
        "Team #",
        "Team Name",
        "Team Code",
        "Individual Trader ID",
        "Password",
        "Email Address",
        "First Name",
        "Last Name",
        "Home School / College",
        "Please enter your information - Primary Degree",
        "Please enter your information - Expected Graduation Year",
        "Are you?",
        "Registering for",
    ])

    # Save
    if out_path.lower().endswith(".xlsx"):
        df_trader.to_excel(out_path, index=False)
    else:
        df_trader.to_csv(out_path, index=False)

    if out_path_team.lower().endswith(".xlsx"):
        df_team.to_excel(out_path_team, index=False)
    else:
        df_team.to_csv(out_path_team, index=False)

    if out_path_reg.lower().endswith(".xlsx"):
        df_reg.to_excel(out_path_reg, index=False)
    else:
        df_reg.to_csv(out_path_reg, index=False)

    print(f"✅ TraderList        → {out_path}   (rows={len(df_trader)})")
    print(f"✅ TeamList (dedup)  → {out_path_team} (teams={len(df_team)})")
    print(f"✅ RegistrationList  → {out_path_reg}  (rows={len(df_reg)})")

# ---------- CLI ----------
def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate Trader/Team/Registration lists, password in col D, TeamList deduped, with optional admin accounts.")
    p.add_argument("--names", required=True, help="Path to Excel/CSV with Team + First + Last columns (email optional).")
    p.add_argument("--out",  default="TraderList.xlsx", help="Trader output file")
    p.add_argument("--out2", default="TeamList.xlsx",   help="Team output file")
    p.add_argument("--out3", default="RegistrationList.xlsx", help="Registration template output file")
    p.add_argument("--team-col",  type=str, default=None, help="Exact team column header (e.g., 'Team')")
    p.add_argument("--first-col", type=str, default=None, help="Exact first-name column header (e.g., 'First Name')")
    p.add_argument("--last-col",  type=str, default=None, help="Exact last-name column header (e.g., 'Last Name')")
    p.add_argument("--email-col", type=str, default=None, help="Exact email column header (e.g., 'BU Email')")
    p.add_argument("--sheet",     type=str, default=None, help="Worksheet name to read (Excel only)")
    p.add_argument("--all-sheets", action="store_true", help="Read and combine all worksheets")
    p.add_argument("--admin-count", type=int, default=0, help="How many admin accounts to create (FRTL-1, FRTL-2, ...)")
    p.add_argument("--admin-prefix", type=str, default="FRTL", help="Admin team prefix (default FRTL)")
    p.add_argument("--seed", type=int, default=None, help="Random seed (affects deterministic password pick)")
    return p.parse_args()

if __name__ == "__main__":
    args = _parse_args()
    generate_users(
        names_path=args.names,
        out_path=args.out,
        out_path_team=args.out2,
        out_path_reg=args.out3,
        team_col_arg=args.team_col,
        first_col_arg=args.first_col,
        last_col_arg=args.last_col,
        email_col_arg=args.email_col,
        sheet=args.sheet,
        all_sheets=args.all_sheets,
        admin_count=args.admin_count,
        admin_prefix=args.admin_prefix,
        seed=args.seed,
    )
