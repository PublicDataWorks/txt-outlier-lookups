import os
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session as OrmSession

from services.analytics.service import AnalyticsService
from services.analytics.utils import generate_major_themes_section

# The broadcast exclusion is a Postgres query, so it needs a real Postgres, e.g.
#   docker run --rm --detach --env POSTGRES_PASSWORD=postgres --publish 127.0.0.1:54392:5432 postgres:15
#   TEST_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54392/postgres pytest tests/test_weekly_report.py
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

BROADCAST = {
    "first_message": "Hi neighbor, this is Outlier. Rent going up this year?\n\nReply YES to tell us more.",
    "second_message": "You can also text an address\nto look up who owns it.",
}


@pytest.fixture
def last_week_messages():
    engine = create_engine(TEST_DATABASE_URL)
    with engine.connect() as conn:
        transaction = conn.begin()
        exists = conn.execute(text("select to_regclass('public.twilio_messages')")).scalar()
        assert exists is None, "TEST_DATABASE_URL must point at an empty, disposable database"
        conn.execute(text("""
            create table public.users (id int primary key, name text, email text);
            create table public.twilio_messages (
                preview text, from_field text, to_field text, "references" text[], sender_id int,
                created_at timestamptz default date_trunc('week', current_date) - interval '3 days'
            );
        """))

        def insert(reference, preview):
            conn.execute(
                text('insert into public.twilio_messages (preview, from_field, to_field, "references") '
                     "values (:preview, '+10000000000', '+10000000001', array[:reference])"),
                {"preview": preview, "reference": reference},
            )

        yield insert, OrmSession(bind=conn)
        transaction.rollback()


@pytest.mark.skipif(not TEST_DATABASE_URL, reason="needs TEST_DATABASE_URL")
def test_messages_history_excludes_broadcast_stored_with_spaces_for_line_breaks(last_week_messages):
    insert, session = last_week_messages
    insert("broadcast", "Hi neighbor, this is Outlier. Rent going up this year? Reply YES to tell us more.")
    insert("reply", "Yes it went up again")

    history = AnalyticsService().get_weekly_messages_history(session, [BROADCAST])

    assert list(history) == ["reply"]


@pytest.mark.skipif(not TEST_DATABASE_URL, reason="needs TEST_DATABASE_URL")
def test_messages_history_excludes_broadcast_stored_without_line_breaks(last_week_messages):
    insert, session = last_week_messages
    insert("broadcast", "You can also text an addressto look up who owns it.")
    insert("reply", "Yes it went up again")

    history = AnalyticsService().get_weekly_messages_history(session, [BROADCAST])

    assert list(history) == ["reply"]


@pytest.mark.skipif(not TEST_DATABASE_URL, reason="needs TEST_DATABASE_URL")
def test_messages_history_excludes_broadcast_whose_non_breaking_spaces_were_rewritten(last_week_messages):
    insert, session = last_week_messages
    insert("broadcast", "Hi neighbor, rent going up? Reply YES.")
    insert("reply", "Yes it went up again")

    broadcast = {"first_message": "Hi\u00a0neighbor, rent going\u202fup? Reply YES.", "second_message": "Thanks"}
    history = AnalyticsService().get_weekly_messages_history(session, [broadcast])

    assert list(history) == ["reply"]


@pytest.mark.skipif(not TEST_DATABASE_URL, reason="needs TEST_DATABASE_URL")
def test_messages_history_excludes_long_broadcast_cut_to_140_characters(last_week_messages):
    insert, session = last_week_messages
    long_broadcast = "Is it ok? " * 30
    insert("broadcast", long_broadcast[:140])
    insert("reply", "Yes it went up again")

    broadcast = {"first_message": long_broadcast, "second_message": "Thanks"}
    history = AnalyticsService().get_weekly_messages_history(session, [broadcast])

    assert list(history) == ["reply"]


@pytest.mark.skipif(not TEST_DATABASE_URL, reason="needs TEST_DATABASE_URL")
def test_messages_history_ignores_blank_broadcast_messages(last_week_messages):
    insert, session = last_week_messages
    insert("reply", "Yes it went up again")

    broadcast = {"first_message": "Hi neighbor, rent going up?", "second_message": " \n "}
    history = AnalyticsService().get_weekly_messages_history(session, [broadcast])

    assert list(history) == ["reply"]


@pytest.mark.skipif(not TEST_DATABASE_URL, reason="needs TEST_DATABASE_URL")
def test_messages_history_keeps_everything_in_a_week_without_broadcasts(last_week_messages):
    insert, session = last_week_messages
    insert("reply", "Yes it went up again")

    history = AnalyticsService().get_weekly_messages_history(session, [])

    assert list(history) == ["reply"]


def test_themes_section_still_renders_when_the_summary_fails():
    with patch("services.analytics.utils.generate_report_summary", side_effect=RuntimeError("model gone")):
        section = generate_major_themes_section({"reference": [{"preview": "hello"}]})

    assert section == "## Summary of Major Themes/Topics\nThe summary could not be generated this week."


def test_themes_section_still_renders_when_the_summary_template_is_missing():
    with patch("services.analytics.utils.generate_report_summary", return_value=None):
        section = generate_major_themes_section({"reference": [{"preview": "hello"}]})

    assert section == "## Summary of Major Themes/Topics\nThe summary could not be generated this week."
