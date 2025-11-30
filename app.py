# app_final.py
import traceback
import re
import gradio as gr
import pandas as pd

# your helper modules (must exist)
from openai_utils import generate_sql_from_query
from db_utils import run_query
from report_generator import generate_dynamic_report
from email_service import send_email_with_report
from decide_utils_upt import decide_email_action
from config import TABLE_SCHEMA_DICT

# --- fixed TABLE_SCHEMA (missing comma fixed) ---
TABLE_SCHEMA = """
HR_DATASET(
    EMPLOYEE_NAME      VARCHAR2(100),
    EMPID              NUMBER,
    SALARY             NUMBER,
    POSITION           VARCHAR2(100),
    STATE              VARCHAR2(50),
    DOB                DATE,
    SEX                VARCHAR2(10),
    MARITALDESC        VARCHAR2(50),
    CITIZENDESC        VARCHAR2(50),
    HISPANICLATINO     VARCHAR2(10),
    RACEDESC           VARCHAR2(50),
    DATEOFHIRE         DATE,
    DATEOFTERMINATION  DATE,
    ON_NOTICEPERIOD    VARCHAR2(10),
    TERMREASON         VARCHAR2(200),
    DEPARTMENT         VARCHAR2(100),
    MANAGERNAME        VARCHAR2(100),
    MANAGERID          NUMBER,
    RECRUITMENTSOURCE  VARCHAR2(100),
    DAYSLATELAST30     NUMBER,
    ABSENCES           NUMBER,
    EMPLOYEE_EMAIL     VARCHAR2(200),
    MANAGER_EMAIL      VARCHAR2(200)
)
"""

# ---- Small helpers ----
def show_table_description_df():
    """Return DataFrame of column -> description (for gr.DataFrame output)."""
    df = pd.DataFrame(
        [(k, v) for k, v in TABLE_SCHEMA_DICT.items()],
        columns=["column_name", "description"]
    )
    return df

# def insert_column_into_query(col_name: str, current_query: str):
#     """Insert the selected column into the query textbox (appends with a space)."""
#     if not col_name:
#         return current_query or ""
#     if not current_query:
#         return f"{col_name} "
#     suffix = "" if current_query.endswith(" ") else " "
#     return current_query + suffix + col_name + " "

# --- Helper that populates email/department dropdowns (attempts DB lookup) ---
def get_indirect_dropdowns(delivery_mode: str):
    """
    Return lists: (email_columns, dept_choices)
    - If delivery_mode contains 'Direct', return empty lists (we clear dropdowns)
    - Otherwise tries to inspect TABLE_SCHEMA_DICT and DB for departments.
    """
    try:
        # IMPORTANT: when Direct selected, we clear both dropdowns (no value)
        if delivery_mode is not None and "Direct" in delivery_mode:
            return [], []

        # Otherwise (Indirect or None) populate from schema + DB
        email_cols = [col for col in TABLE_SCHEMA_DICT.keys() if "EMAIL" in col.upper()]

        # try to fetch distinct departments from DB
        dept_choices = []
        try:
            df_dept = run_query("SELECT DISTINCT DEPARTMENT FROM HR_DATASET ORDER BY DEPARTMENT")
            if isinstance(df_dept, pd.DataFrame) and not df_dept.empty:
                colname = df_dept.columns[0]
                dept_choices = [str(v) for v in df_dept[colname].dropna().tolist()]
        except Exception:
            traceback.print_exc()
            dept_choices = []

        return email_cols, dept_choices
    except Exception:
        traceback.print_exc()
        return [], []

# wrapper to return gr.update results (clears values correctly for Direct)
def gr_get_indirect_dropdowns(delivery_mode: str):
    email_cols, dept_choices = get_indirect_dropdowns(delivery_mode)
    # ensure uniqueness & string conversion
    email_cols = [str(x) for x in dict.fromkeys(email_cols)]
    dept_choices = [str(x) for x in dict.fromkeys(dept_choices)]

    # If user chose Direct, get_indirect_dropdowns returns empty lists -> we set value None
    if delivery_mode is not None and "Direct" in delivery_mode:
        return gr.update(choices=[], value=None), gr.update(choices=[], value=None)

    # Otherwise set choices and sensible defaults (first option if available)
    email_value = email_cols[0] if email_cols else None
    dept_value = dept_choices[0] if dept_choices else None
    return gr.update(choices=email_cols, value=email_value), gr.update(choices=dept_choices, value=dept_value)


# --- Core functions used by UI (stateless wrt Gradio) ---
def process_query(user_prompt: str):
    """
    Convert user NL prompt to SQL, run it, return DataFrame.
    This function returns two values for Gradio wiring: df_output and last_df_state.
    """
    try:
        sql_query = generate_sql_from_query(user_prompt, TABLE_SCHEMA)
        df = run_query(sql_query)
        if df is None:
            df = pd.DataFrame()
    except Exception as e:
        traceback.print_exc()
        df = pd.DataFrame()
    # Return df for display and store it in state
    return df, df

def ai_preview(user_instruction: str,
               delivery_action: str,
               selected_email_col: str,
               selected_department: str,
               last_df):
    """
    Calls decide_email_action with full signature and returns (preview_markdown, pending_decision_dict).
    Gradio will store pending_decision_dict into a gr.State.
    """
    # allow last_df to be None (decide_email_action will fallback to DB)
    try:
        decision = decide_email_action(
            user_instruction=user_instruction,
            table_schema=TABLE_SCHEMA,
            dataframe=last_df,
            delivery_action=delivery_action,
            email_col=selected_email_col,
            department=selected_department
        )
    except Exception as e:
        traceback.print_exc()
        decision = {
            "action": "ai_decision",
            "recipients": [],
            "email_column": selected_email_col,
            "department": selected_department,
            "decision": f"Error running decision logic: {e}",
            "draft": None
        }

    # Build friendly preview markdown
    action = decision.get("action", "ai_decision")
    recipients = decision.get("recipients", []) or []
    draft = decision.get("draft")
    if action in ("direct", "indirect"):
        recips_preview = "\n".join(recipients[:200]) if recipients else "(no recipients)"
        more = f"\n... and {len(recipients)-200} more" if len(recipients) > 200 else ""
        md = f"**AI Decision:** `{action}`\n\n**Recipients ({len(recipients)}):**\n```\n{recips_preview}{more}\n```"
        if draft:
            md += f"\n\n**Draft (preview):**\n```\n{draft[:800]}{('...' if len(draft)>800 else '')}\n```"
        md += f"\n\n**Note:** {decision.get('decision')}"
    else:
        md = f"**AI Decision (info):**\n\n{decision.get('decision')}\n"
        if draft:
            md += f"\n\n**Draft (preview):**\n```\n{draft[:800]}{('...' if len(draft)>800 else '')}\n```"

    return md, decision

def confirm_and_send(pending_decision, last_df):
    """
    Send report to recipients from pending_decision (which must be the dict returned by decide_email_action).
    Returns status string for UI.
    """
    if not pending_decision:
        return "⚠️ Please preview first."

    action = pending_decision.get("action", "")
    recipients = pending_decision.get("recipients", []) or []

    if action not in ("direct", "indirect"):
        return f"⚠️ Action is '{action}' — nothing to send. Decision: {pending_decision.get('decision')}"

    if not recipients:
        return f"⚠️ No recipients found for action '{action}'. Decision: {pending_decision.get('decision')}"

    # dedupe & normalize
    seen = set(); deduped = []
    for r in recipients:
        rr = str(r).strip()
        if rr and rr not in seen:
            seen.add(rr); deduped.append(rr)

    # generate the report
    try:
        report_path = generate_dynamic_report(last_df)
    except Exception as e:
        traceback.print_exc()
        return f"❌ Failed to generate report: {e}"

    successes = []
    failures = []
    email_body_template = pending_decision.get("draft") or "Hello,\n\nPlease find the requested report attached.\n\nRegards,\nAI Oracle Assistant"

    # send one-by-one
    for email in deduped:
        try:
            send_email_with_report(
                to_email=email,
                subject="Automated HR Report",
                body=email_body_template,
                attachment_path=report_path
            )
            successes.append(email)
        except Exception as e:
            traceback.print_exc()
            failures.append({"email": email, "error": str(e)})

    summary = f"✅ Sent: {len(successes)}. Failures: {len(failures)}."
    if failures:
        sample = "; ".join([f"{f['email']} ({f['error']})" for f in failures[:5]])
        summary += f" Sample failures: {sample}"
    return summary

# ----------------------- Gradio UI -----------------------
with gr.Blocks() as demo:
    gr.Markdown("## 📧 AI Oracle HR Email Assistant with AI Decision Preview")

    # Always-visible table description at top
    schema_output = gr.DataFrame(value=show_table_description_df(), label="HR Table Description (column, meaning)", interactive=False)

    # --- Query area ---
    query_input = gr.Textbox(label="Enter your HR question", lines=2)
    query_button = gr.Button("Run Query")
    df_output = gr.DataFrame()   # shows results

    # --- Radio button / Dropdowns ---
    delivery_radio = gr.Radio(choices=["Indirect (by table)", "Direct (manual emails)"], label="Delivery mode", value=None)
    email_col_dropdown = gr.Dropdown(choices=[], label="Select email column (auto-detected)", value=None, interactive=True)
    dept_dropdown = gr.Dropdown(choices=[], label="Select Department (distinct values)", value=None, interactive=True)

    # Populate dropdowns when delivery mode changes
    delivery_radio.change(fn=gr_get_indirect_dropdowns, inputs=[delivery_radio], outputs=[email_col_dropdown, dept_dropdown])

    # state objects
    selected_email_col_state = gr.State(value=None)
    selected_dept_state = gr.State(value=None)
    last_df_state = gr.State(value=None)
    pending_decision_state = gr.State(value=None)

    # small functions to save dropdown values (defined inline above) - will store the raw value into state
    def save_email(val): return val
    def save_dept(val): return val

    email_col_dropdown.change(save_email, inputs=email_col_dropdown, outputs=selected_email_col_state)
    dept_dropdown.change(save_dept, inputs=dept_dropdown, outputs=selected_dept_state)

    # --- Follow-up / AI decision area ---
    instruction_input = gr.Textbox(label="Follow-up Instruction (e.g., 'Send this to department heads')", lines=2)
    preview_btn = gr.Button("🔍 AI Decide Recipients")
    preview_output = gr.Markdown()

    # --- Confirm & send area ---
    confirm_btn = gr.Button("✅ Confirm & Send")
    confirm_output = gr.Textbox(label="Status")

    # wiring
    query_button.click(process_query, inputs=query_input, outputs=[df_output, last_df_state])

    # preview: pass instruction + delivery mode + saved states + last_df_state
    preview_btn.click(
        fn=ai_preview,
        inputs=[instruction_input, delivery_radio, selected_email_col_state, selected_dept_state, last_df_state],
        outputs=[preview_output, pending_decision_state]
    )

    # confirm: use pending_decision_state and last_df_state
    confirm_btn.click(
        fn=confirm_and_send,
        inputs=[pending_decision_state, last_df_state],
        outputs=confirm_output
    )

if __name__ == "__main__":
    demo.launch()

