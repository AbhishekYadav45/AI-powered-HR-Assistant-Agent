import re
import pandas as pd
from typing import Optional, Dict, Any
from db_utils import run_query  # your existing DB helper

EMAIL_REGEX = r"[\w\.\-+%]+@[\w\.\-]+\.[A-Za-z]{2,}"

# ---------------- Helpers ----------------

def _find_department_column(df: pd.DataFrame) -> Optional[str]:
    """Find a department-like column (e.g., 'DEPARTMENT', 'Dept')."""
    for c in df.columns:
        if re.search(r"\b(department|dept)\b", str(c), flags=re.IGNORECASE):
            return c
    return None

def _sum_value_from_df(df: pd.DataFrame, department: Optional[str]) -> float:
    """
    Return the SUM of the first numeric column (or row count as fallback).
    Always treated as a 'value' (never 'count').
    """
    if df is None or df.empty:
        return 0.0

    df2 = df
    dept_col = _find_department_column(df)
    if department and dept_col and dept_col in df.columns:
        df2 = df[df[dept_col].astype(str).str.strip().str.casefold() == department.strip().casefold()]

    numeric_cols = df2.select_dtypes(include="number").columns.tolist()
    if numeric_cols:
        return float(df2[numeric_cols[0]].sum())

    # Fallback: number of rows (still considered a value)
    return float(len(df2))

def _fixed_summary_draft(department: Optional[str], value: float) -> str:
    """Compose the email body using 'total employee value' wording."""
    v = f"{int(value):,}" if value.is_integer() else f"{value:,.2f}"

    if department:
        line1 = f"Please be informed that the total employee value in the {department} department is {v}."
    else:
        line1 = f"Please be informed that the total employee value is {v}."

    return "\n".join([
        "Hi,",
        "",
        line1,
        "Should you require any further details, please refer to the attached document.",
        "",
        "Thanks & Regards,",
        "HR"
    ])

# ---------------- Main decision function (structure preserved) ----------------

def decide_email_action(
    user_instruction: str,
    table_schema: str,
    dataframe: Optional[pd.DataFrame] = None,
    delivery_action: Optional[str] = None,
    email_col: Optional[str] = None,
    department: Optional[str] = None
) -> Dict[str, Any]:
    """
    Decide recipients and generate an email draft with SUM of values (worded as 'total employee value').
    Returns dict with keys:
      - action: "direct" | "indirect" | "ai_decision"
      - recipients: list of emails (may be empty)
      - email_column, department
      - decision: readable message
      - draft: str | None
    """
    ui = (user_instruction or "").strip()
    delivery = (delivery_action or "").strip()

    # Prepare draft -> FIXED TEMPLATE using SUM
    draft_text: Optional[str] = None
    try:
        if isinstance(dataframe, pd.DataFrame) and len(dataframe) >= 1:
            total_val = _sum_value_from_df(dataframe, department)
            draft_text = _fixed_summary_draft(department, total_val)
    except Exception:
        try:
            if isinstance(dataframe, pd.DataFrame) and len(dataframe) >= 1:
                total_val = _sum_value_from_df(dataframe, department)
                draft_text = _fixed_summary_draft(department, total_val)
        except Exception:
            draft_text = None

    # Basic guard
    if not ui and not delivery:
        return {
            "action": "ai_decision",
            "recipients": [],
            "email_column": email_col,
            "department": department,
            "decision": "Please provide an instruction or select a delivery mode (Direct/Indirect).",
            "draft": draft_text
        }

    # 1) explicit emails in instruction -> direct
    found_emails = re.findall(EMAIL_REGEX, ui)
    if found_emails:
        seen, recipients = set(), []
        for e in found_emails:
            e = e.strip()
            if e and e not in seen:
                seen.add(e)
                recipients.append(e)
        return {
            "action": "direct",
            "recipients": recipients,
            "email_column": email_col,
            "department": department,
            "decision": f"Found {len(recipients)} explicit email(s) in instruction.",
            "draft": draft_text
        }

    # 2) Direct chosen but no emails -> ask user
    if delivery and "Direct" in delivery:
        return {
            "action": "ai_decision",
            "recipients": [],
            "email_column": email_col,
            "department": department,
            "decision": "Direct delivery selected but no email addresses found in instruction. Please provide comma-separated emails.",
            "draft": draft_text
        }

    # 3) Indirect path
    if delivery and "Indirect" in delivery:
        if not email_col:
            return {
                "action": "ai_decision",
                "recipients": [],
                "email_column": email_col,
                "department": department,
                "decision": "Please select an email column for indirect lookup.",
                "draft": draft_text
            }
        if not department:
            return {
                "action": "ai_decision",
                "recipients": [],
                "email_column": email_col,
                "department": department,
                "decision": "Please select a department for indirect lookup.",
                "draft": draft_text
            }

        values, sql_used = [], None
        try:
            if isinstance(dataframe, pd.DataFrame):
                df = dataframe.copy()
                email_col_actual = None
                if email_col in df.columns:
                    email_col_actual = email_col
                else:
                    cols_map = {c.upper(): c for c in df.columns}
                    if email_col and email_col.upper() in cols_map:
                        email_col_actual = cols_map[email_col.upper()]
                    else:
                        candidates = [c for c in df.columns if "EMAIL" in c.upper()]
                        if candidates:
                            email_col_actual = candidates[0]

                if email_col_actual:
                    dept_col = next((c for c in df.columns if "DEPARTMENT" in c.upper() or "DEPT" in c.upper()), None)
                    if dept_col:
                        mask = df[dept_col].astype(str).str.strip() == str(department).strip()
                        candidate_series = df.loc[mask, email_col_actual]
                    else:
                        candidate_series = df[email_col_actual]
                    values = candidate_series.dropna().astype(str).tolist()
                else:
                    dataframe = None  # fallback

            if not isinstance(dataframe, pd.DataFrame):
                dept_escaped = str(department).replace("'", "''")
                sql_used = f"SELECT DISTINCT {email_col} FROM HR_DATASET WHERE DEPARTMENT = '{dept_escaped}'"
                df_emails = run_query(sql_used)
                if df_emails is not None and not df_emails.empty:
                    colname = df_emails.columns[0]
                    values = df_emails[colname].dropna().astype(str).tolist()

        except Exception as e:
            return {
                "action": "ai_decision",
                "recipients": [],
                "email_column": email_col,
                "department": department,
                "decision": f"Error while collecting recipients: {e}",
                "draft": draft_text
            }

        # Parse emails
        recipients, seen = [], set()
        for v in values:
            for p in re.split(r"[;,]\s*", v.strip()):
                if p and re.match(EMAIL_REGEX, p) and p not in seen:
                    seen.add(p)
                    recipients.append(p)

        if not recipients:
            extra = f" SQL: {sql_used}" if sql_used else ""
            return {
                "action": "ai_decision",
                "recipients": [],
                "email_column": email_col,
                "department": department,
                "decision": f"No valid email addresses found for the chosen column/department.{extra}",
                "draft": draft_text
            }

        decision_msg = f"Found {len(recipients)} recipient(s) for department '{department}'."
        if sql_used:
            decision_msg += f" SQL: {sql_used}"

        return {
            "action": "indirect",
            "recipients": recipients,
            "email_column": email_col,
            "department": department,
            "decision": decision_msg,
            "draft": draft_text
        }

    # Fallback
    return {
        "action": "ai_decision",
        "recipients": [],
        "email_column": email_col,
        "department": department,
        "decision": "Could not decide. Please check your inputs.",
        "draft": draft_text
    }
