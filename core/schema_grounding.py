def schema_text(sqldb) -> str:
    # includes sample rows (configured in SQLDatabase)
    return sqldb.get_table_info()