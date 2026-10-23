from main import app


def test_empty_app_generates_openapi_schema() -> None:
    schema = app.openapi()

    assert schema["info"]["title"] == "Personal Expense Tracker API"
    assert schema["paths"] == {}
