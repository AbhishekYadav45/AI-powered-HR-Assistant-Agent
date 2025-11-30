import re
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_MODEL

client = OpenAI(api_key=OPENAI_API_KEY)

def generate_sql_from_query(user_prompt: str, table_schema: str) -> str:
    """
    Uses OpenAI to convert natural language into SQL query.
    Cleans the response so only pure SQL is returned (no explanations/markdown).
    """
    messages = [
        {"role": "system", "content": f"""You are a data assistant working with Oracle SQL.
        Use this schema:\n{table_schema}.
        when you where clause use upper() and upper alfabet letter in condtion and make it single line and  should not used symbole ; at end due error.
        Always return only a valid SQL query.
        Do NOT include explanations, comments, or markdown.
        HR_DATASET colunm details
        EMPID : UNIQUE IDENTIFIER ASSIGNED TO EACH EMPLOYEE
        SALARY : CURRENT OR LAST DRAWN SALARY OF THE EMPLOYEE
        POSITION : JOB TITLE/ROLE OF THE EMPLOYEE (E.G., TECHNICIAN, ENGINEER)
        STATE : WORK LOCATION (STATE) OF THE EMPLOYEE
        DOB : DATE OF BIRTH OF THE EMPLOYEE
        SEX : GENDER OF THE EMPLOYEE (M/F)
        MARITALDESC : MARITAL STATUS (SINGLE, MARRIED, DIVORCED, WIDOWED)
        CITIZENDESC : CITIZENSHIP STATUS (E.G., US CITIZEN)
        HISPANICLATINO : WHETHER EMPLOYEE IS HISPANIC/LATINO (YES/NO)
        RACEDESC : RACIAL/ETHNIC BACKGROUND OF THE EMPLOYEE
        DATEOFHIRE : DATE WHEN THE EMPLOYEE JOINED THE COMPANY
        DATEOFTERMINATION : LAST WORKING DATE (BLANK IF STILL EMPLOYED)
        ON_NOTICEPERIOD : WHETHER EMPLOYEE IS CURRENTLY SERVING NOTICE (YES/NO)
        TERMREASON : REASON FOR TERMINATION/EXIT (E.G., CAREER CHANGE, UNHAPPY)
        DEPARTMENT : DEPARTMENT THE EMPLOYEE BELONGS TO (E.G., IT, PRODUCTION)
        MANAGERNAME : NAME OF THE REPORTING MANAGER
        MANAGERID : UNIQUE ID OF THE REPORTING MANAGER
        RECRUITMENTSOURCE : SOURCE THROUGH WHICH EMPLOYEE WAS RECRUITED (LINKEDIN, INDEED, REFERRAL)
        DAYSLATELAST30 : NUMBER OF DAYS EMPLOYEE WAS LATE IN THE LAST 30 DAYS
        ABSENCES : TOTAL NUMBER OF ABSENCES RECORDED
        EMPLOYEE_EMAIL  : EMPLOYEE’S (EMP) EMAIL ADDRESS COLUMN  
        MANAGER_EMAIL  : MANAGER'S EMAIL ADDRESS COLUMN  
        
        """},
        {"role": "user", "content": user_prompt}
    ]

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=0
    )

    # ✅ Access content correctly for your SDK version
    raw_sql = response.choices[0].message.content.strip()

    # ✅ Remove markdown fences
    raw_sql = re.sub(r"```sql|```", "", raw_sql).strip()

    # ✅ Extract only SQL lines
    sql_lines = []
    capture = False
    for line in raw_sql.splitlines():
        line_stripped = line.strip()
        if line_stripped.lower().startswith(("select", "with", "insert", "update", "delete", "create")):
            capture = True
            sql_lines.append(line_stripped)
        elif capture:
            if line_stripped:
                sql_lines.append(line_stripped)

    if sql_lines:
        cleaned_sql = "\n".join(sql_lines).strip()
        print("\n✅ Cleaned SQL to execute:\n", cleaned_sql)  # Debug print
        return cleaned_sql

    return raw_sql