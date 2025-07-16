def clean_sql(sql: str) -> str:
    """Remove Markdown SQL block formatting."""
    sql = sql.strip()
    if sql.startswith("```sql"):
        sql = sql.replace("```sql", "").strip()
    if sql.endswith("```"):
        sql = sql[:-3].strip()
    return sql