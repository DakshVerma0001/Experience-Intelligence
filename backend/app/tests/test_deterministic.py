from app.services.extraction import deterministic, normalizer


def test_extract_emails():
    assert deterministic.extract_emails("Contact: raj.kumar@nabard.org for details") == ["raj.kumar@nabard.org"]


def test_extract_currency_mentions_with_cue():
    hits = deterministic.extract_currency_mentions("Approx. value of the Contract: Rs. 3.16 Crores")
    assert hits
    raw, unit, full = hits[0]
    assert raw.replace(" ", "") == "3.16"
    assert "crore" in unit.lower()


def test_extract_currency_ignores_numbers_without_cue():
    hits = deterministic.extract_currency_mentions("Staff strength of 25 people over 36 months")
    assert hits == []


def test_extract_assignment_number():
    assert deterministic.extract_assignment_number("Assignment-14") == "Assignment-14"
    assert deterministic.extract_assignment_number("Assignment # 3: PACS") == "Assignment-3"
    assert deterministic.extract_assignment_number("No marker here") is None


def test_extract_dates_month_year():
    dates = deterministic.extract_dates("Start date: September 2021, Finish date: Ongoing")
    assert "September 2021" in dates
    assert "Ongoing" in dates


def test_normalize_currency_to_crore_handles_messy_spacing():
    value = normalizer.normalize_currency_to_crore("1. 95", "c ore")
    assert value == 1.95


def test_normalize_currency_lakh_to_crore():
    value = normalizer.normalize_currency_to_crore("50", "lakh")
    assert value == 0.5


def test_normalize_date_month_precision_never_invents_day():
    value, precision = normalizer.normalize_date("September 2021")
    assert value == "2021-09"
    assert precision == "month"


def test_normalize_date_ongoing():
    value, precision = normalizer.normalize_date("Ongoing")
    assert value == "Ongoing"
    assert precision == "ongoing"


def test_normalize_project_status_requires_explicit_wording():
    assert normalizer.normalize_project_status("September 2021 - Ongoing") == "Ongoing"
    assert normalizer.normalize_project_status(None) == "Unknown"
    assert normalizer.normalize_project_status("Started in 2019") == "Unknown"


def test_extract_labeled_fields_handles_label_on_own_line():
    lines = ["Name of Client:", "NABARD, Mumbai", "Telephone: 022-12345678"]
    fields = deterministic.extract_labeled_fields(lines)
    assert fields["client_name"][0] == "NABARD, Mumbai"
    assert fields["telephone"][0] == "022-12345678"
