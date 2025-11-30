# db_utils.py - Oracle DB utilities
import oracledb
import pandas as pd
from config import ORACLE_CONFIG

def run_query(sql_query: str) -> pd.DataFrame:
    """
    Executes Oracle SQL and returns a Pandas DataFrame.
    """
    try:
        with oracledb.connect(**ORACLE_CONFIG) as conn:
            df = pd.read_sql(sql_query, conn)
        return df
    except Exception as e:
        return pd.DataFrame({"Error": [str(e)]})