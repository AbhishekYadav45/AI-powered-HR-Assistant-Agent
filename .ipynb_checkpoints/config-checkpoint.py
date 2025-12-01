# config.py - Configuration file

ORACLE_CONFIG = {
    "user": "SYSTEM",
    "password": "system",
    "dsn": "localhost:1521/XEPDB1"
}

TABLE_SCHEMA_DICT = {
    "EMPID": "Unique identifier assigned to each employee.",
    "SALARY": "Current or last drawn salary of the employee.",
    "POSITION": "Job title/role of the employee (e.g., Technician, Engineer).",
    "STATE": "Work location (state) of the employee.",
    "DOB": "Date of birth of the employee.",
    "SEX": "Gender of the employee (M/F).",
    "MARITALDESC": "Marital status (Single, Married, Divorced, Widowed).",
    "CITIZENDESC": "Citizenship status (e.g., US Citizen).",
    "HISPANICLATINO": "Whether employee is Hispanic/Latino (Yes/No).",
    "RACEDESC": "Racial/ethnic background of the employee.",
    "DATEOFHIRE": "Date when the employee joined the company.",
    "DATEOFTERMINATION": "Last working date (blank if still employed).",
    "ON_NOTICEPERIOD": "Whether employee is currently serving notice (YES/NO).",
    "TERMREASON": "Reason for termination/exit (e.g., career change, unhappy).",
    "DEPARTMENT": "Department the employee belongs to (e.g., IT, Production).",
    "MANAGERNAME": "Name of the reporting manager.",
    "MANAGERID": "Unique ID of the reporting manager.",
    "RECRUITMENTSOURCE": "Source through which employee was recruited (LinkedIn, Indeed, Referral).",
    "DAYSLATELAST30": "Number of days employee was late in the last 30 days.",
    "ABSENCES": "Total number of absences recorded.",
    "EMPLOYEE_EMAIL": "Employee's email address.",
    "MANAGER_EMAIL": "Manager's email address."
}

OPENAI_MODEL = "gpt-4o-mini"
OPENAI_API_KEY = "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"

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "cse.abhishekyadav45@gmail.com"
SENDER_PASSWORD = "iinswcmxlsjgenvm"
