from core.sql_safety import is_read_only_select, enforce_limit


def test_unsafe_sql_blocked():
    assert is_read_only_select('DROP TABLE Customers') is False
    assert is_read_only_select('DELETE FROM Orders') is False
    assert is_read_only_select('SELECT * FROM Customers') is True


def test_count_query_gets_no_limit():
    sql = 'SELECT COUNT(*) FROM Products'
    result = enforce_limit(sql, default_limit=200, max_limit=1000)
    assert "LIMIT" not in result.upper()


def test_grouped_query_still_gets_limit():
    sql = 'SELECT "CustomerID", COUNT(*) FROM Orders GROUP BY "CustomerID"'
    result = enforce_limit(sql, default_limit=200, max_limit=1000)
    assert "LIMIT 200" in result.upper()