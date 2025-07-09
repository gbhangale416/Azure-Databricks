import pyodbc
import pandas as pd

def get_sql_connection(server, database, username=None, password=None, use_windows_auth=False):
    """
    Returns a pyodbc connection to the SQL Server
    """
    if use_windows_auth:
        conn_str = f'''
            DRIVER={{ODBC Driver 17 for SQL Server}};
            SERVER={server};
            DATABASE={database};
            Trusted_Connection=yes;
            TrustServerCertificate=yes;
        '''
    else:
        conn_str = f'''
            DRIVER={{ODBC Driver 17 for SQL Server}};
            SERVER={server};
            DATABASE={database};
            UID={username};
            PWD={password};
            TrustServerCertificate=yes;
        '''
    return pyodbc.connect(conn_str)

def query_table_as_dataframe(conn, table_name):
    """
    Queries the table and returns a pandas DataFrame
    """
    query = f"SELECT * FROM {table_name}"
    return pd.read_sql(query, conn)

# 🔧 Example usage
if __name__ == "__main__":
    # Replace with your actual values
    server = "192.168.1.10"  # On-prem SQL Server IP or hostname
    database = "my_database"
    username = "my_user"
    password = "my_password"
    table_name = "my_table"

    # Get connection (set use_windows_auth=True for Windows Auth)
    conn = get_sql_connection(server, database, username, password, use_windows_auth=False)

    # Load data into DataFrame
    df = query_table_as_dataframe(conn, table_name)
    print(df.head())

    conn.close()
