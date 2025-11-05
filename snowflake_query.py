import os
import snowflake.connector
import argparse

def get_snowflake_connection():
    """Create and return a Snowflake connection using environment variables."""
    return snowflake.connector.connect(
        user=os.environ["SNOWFLAKE_USER"],
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        role=os.environ["SNOWFLAKE_ROLE"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        database=os.environ["SNOWFLAKE_DATABASE"],
        authenticator=os.environ.get("SNOWFLAKE_AUTHENTICATOR", "snowflake"),
        password=os.environ["SNOWSQL_PWD"]
    )

def execute_snowflake_query(query, autocommit=True, verbose=True):
    """Execute a SQL query on Snowflake and print the result."""
    conn = None
    try:
        conn = get_snowflake_connection()
        if not autocommit:
            conn.autocommit(False)

        if verbose:
            print(f"Executing query:\n{query}\n")

        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()

        # Print results if available
        if results:
            for row in results:
                print(row)
        else:
            print("Query executed successfully (no results returned).")

        if not autocommit:
            conn.commit()
    except Exception as e:
        if conn and not autocommit:
            conn.rollback()
        print(f"❌ Error executing query: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Execute a SQL query on Snowflake.")
    parser.add_argument("-q", "--query", type=str, required=True, help="SQL query to execute on Snowflake.")
    parser.add_argument("-ac", "--autocommit", action="store_true", help="Enable autocommit mode.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output.")
    args = parser.parse_args()

    execute_snowflake_query(args.query, args.autocommit, args.verbose)
