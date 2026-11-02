from app.services.validation.validator import validate_project


def test_validate_project_passed():
    result = validate_project(
        {
            "project_name": "GIS Platform",
            "client_name": "State Government",
            "project_description": "A description",
            "email": "a@b.com",
            "contract_value_crore": 1.5,
            "extraction_confidence": 0.9,
            "keywords": [{"keyword": "GIS"}],
        }
    )
    assert result.status == "PASSED"
    assert result.warnings == []


def test_validate_project_missing_critical_fields():
    result = validate_project({"project_name": None, "client_name": None, "project_description": None})
    assert result.status == "FAILED"
    assert "project_name" in result.missing_critical_fields


def test_validate_project_warning_on_low_confidence():
    result = validate_project(
        {
            "project_name": "X",
            "client_name": "Y",
            "project_description": "Z",
            "extraction_confidence": 0.3,
            "keywords": [{"keyword": "A"}],
        }
    )
    assert result.status == "WARNING"
    assert any("confidence" in w.lower() for w in result.warnings)
