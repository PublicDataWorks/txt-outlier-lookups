import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

# Sessions only go wrong against a real Postgres that drops their connection, e.g.
#   docker run --rm --detach --env POSTGRES_PASSWORD=postgres --publish 127.0.0.1:54392:5432 postgres:15
#   TEST_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54392/postgres pytest tests/test_database_sessions.py
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
REPO = Path(__file__).resolve().parents[1]
PHONE = "+15550001234"
LOOKUP_TAG = "lookup-tag"

pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="needs TEST_DATABASE_URL")


@pytest.fixture(scope="module", autouse=True)
def database():
    engine = create_engine(TEST_DATABASE_URL, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        exists = conn.execute(text("select to_regclass('public.lookup_template')")).scalar()
        assert exists is None, "TEST_DATABASE_URL must point at an empty, disposable database"
        conn.execute(text("""
            create table public.lookup_template (
                id bigserial primary key, created_at timestamptz, updated_at timestamptz,
                name text unique, content text, type text
            );
            insert into public.lookup_template (name, content) values
                ('max_tokens', '1000'), ('sms_history_summary', 'Summarize the replies'),
                ('no_match', 'No match for {address}');
            create table public.twilio_messages (
                id uuid primary key default gen_random_uuid(), preview text, delivered_at timestamptz,
                from_field text, to_field text
            );
        """))
        conn.execute(text("insert into public.twilio_messages (preview, delivered_at, from_field) "
                          "values ('1 Main St', now(), :phone)"), {"phone": PHONE})
        yield
        conn.execute(text("drop table public.lookup_template, public.twilio_messages"))
    engine.dispose()


# Each run is a fresh app process, because the sessions under test are created when modules import.
DATABASE_PROBES = """
import gc, os
import dotenv
from sqlalchemy import create_engine, text

# The app loads .env with override=True, which would swap a developer's own DATABASE_URL in for the
# disposable one. Keep .env for anything else, but never let it replace what run_app sets.
load_dotenv = dotenv.load_dotenv
dotenv.load_dotenv = lambda *args, **kwargs: load_dotenv(*args, **{**kwargs, "override": False})

# On production a lookup's connection stayed open in its transaction for 8 hours after the response,
# so the garbage collector can't be relied on to close what the app leaves open.
gc.disable()
probe = create_engine(os.environ["DATABASE_URL"], isolation_level="AUTOCOMMIT",
                      connect_args={"application_name": "test-probe"})

def app_connections(condition):
    with probe.connect() as conn:
        return conn.execute(text(
            "select pid from pg_stat_activity where application_name = 'app-under-test' and " + condition
        )).scalars().all()

def open_transactions():
    return len(app_connections("state like 'idle in transaction%'"))

def drop_app_connections():
    # The pooler or the network can close an idle connection; the app finds out on its next query.
    with probe.connect() as conn:
        for pid in app_connections("true"):
            conn.execute(text("select pg_terminate_backend(:pid, 5000)"), {"pid": pid})

def outcome(call):
    try:
        return call()
    except Exception as error:
        return type(error).__name__
"""


def run_app(script):
    env = {key: value for key, value in os.environ.items() if key != "SENTRY_DNS"}
    env.update(DATABASE_URL=TEST_DATABASE_URL, PGAPPNAME="app-under-test", MISSIVE_LOOKUP_TAG_ID=LOOKUP_TAG)
    app = subprocess.run([sys.executable, "-c", DATABASE_PROBES + script], cwd=REPO, env=env,
                         capture_output=True, text=True, timeout=120, check=True)
    return app.stdout.strip().splitlines()[-1]


def test_the_template_cache_reloads_after_its_connection_is_dropped():
    reloads = run_app("""
from configs.cache_template import get_lookup_templates
drop_app_connections()
print([outcome(lambda: len(get_lookup_templates())) for _ in range(2)])
""")

    assert reloads == "[3, 3]"


def test_the_weekly_report_reads_its_prompt_after_its_connection_is_dropped():
    prompts = run_app("""
from unittest.mock import patch
import configs.query_engine.weekly_report_trend_summary as weekly

with patch.object(weekly, "build_llm"), patch.object(weekly, "DocumentSummaryIndex") as index:
    weekly.generate_report_summary({})
    drop_app_connections()
    weekly.generate_report_summary({})
    weekly.generate_report_summary({})
    ask = index.from_documents.return_value.as_query_engine.return_value.query
    print(len([call for call in ask.call_args_list if call.args == ("Summarize the replies",)]))
""")

    assert prompts == "3"


def test_starting_the_app_leaves_no_transaction_open():
    left_open = run_app("""
import main
print(open_transactions())
""")

    assert left_open == "0"


def test_a_gunicorn_worker_gets_its_own_connection_and_leaves_the_masters_open():
    connections = run_app("""
import os, runpy
import main
from configs.database import Session

def server_pid():
    with Session() as session:
        return session.execute(text("select pg_backend_pid()")).scalar()

master = server_pid()
gunicorn_config = runpy.run_path("gunicorn.conf.py")
read, write = os.pipe()
if os.fork() == 0:
    gunicorn_config.get("post_fork", lambda server, worker: None)(None, None)
    os.write(write, str(server_pid()).encode())
    os._exit(0)
os.wait()
worker = int(os.read(read, 32))
print({"worker uses the master connection": worker == master, "master connection kept": server_pid() == master})
""")

    assert connections == "{'worker uses the master connection': False, 'master connection kept': True}"


LOOKUP_ROUTES = """
from unittest.mock import patch
import main

property_queries = []

def property_query(session, address, sunit):
    # The real query needs PostGIS and pg_trgm; any query on the session the route hands over will do.
    property_queries.append(address)
    session.execute(text("select 1"))
    return []

webhook = {"conversation": {"id": "conversation-1", "shared_labels": [{"id": "%s"}]},
           "message": {"from_field": {"id": "%s"}, "preview": "1 Main St"}}
before = open_transactions()
with patch("services.services.extract_address_information_with_llm", return_value=("1 MAIN ST", None)), \\
        patch.object(main, "extract_address_information_with_llm", return_value=("1 MAIN ST", None)), \\
        patch("services.services.query_mi_wayne_detroit", property_query), \\
        patch.object(main, "query_mi_wayne_detroit", property_query), \\
        patch("services.services.missive_client"):
    main.app.test_client().post("%s", json=webhook)
print({"property queries": len(property_queries), "left open": open_transactions() - before})
"""


@pytest.mark.parametrize("route", ["/search", "/yes", "/more"])
def test_a_lookup_leaves_no_transaction_open(route):
    lookup = run_app(LOOKUP_ROUTES % (LOOKUP_TAG, PHONE, route))

    assert lookup == "{'property queries': 1, 'left open': 0}"
