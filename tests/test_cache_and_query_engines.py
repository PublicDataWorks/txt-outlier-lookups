import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from flask import Flask
from flask_caching import Cache
from configs.cache_template import (
    get_lookup_templates,
    init_lookup_templates_cache,
    get_template_content_by_name,
    update_lookup_templates_cache,
    get_tax_message,
    get_rental_message,
)
from configs.query_engine.owner_information import init_owner_query_engine
from configs.query_engine.owner_information_without_sunit import init_owner_query_engine_without_sunit
from configs.query_engine.tax_information import init_tax_query_engine
from configs.query_engine.tax_information_without_sunit import init_tax_query_engine_without_sunit
from configs.supabase import connect_to_supabase, run_websocket_listener

# Mock data
mock_templates = [
    {"name": "no_match", "content": "No match for {address}"},
    {"name": "wrong_format", "content": "Wrong format"},
    {"name": "has_tax_debt", "content": "Has tax debt"},
]

# Initialize Flask app and cache for testing
app = Flask(__name__)
cache = Cache(app, config={"CACHE_TYPE": "SimpleCache"})


def test_get_lookup_templates():
    with patch('configs.cache_template.session') as mock_session:
        mock_query = MagicMock()
        mock_query.all.return_value = [type('Template', (object,), template) for template in mock_templates]
        mock_session.query.return_value = mock_query

        templates = get_lookup_templates()
        assert len(templates) == len(mock_templates)
        assert templates[0]['name'] == mock_templates[0]['name']


def test_init_lookup_templates_cache():
    with patch('configs.cache_template.get_lookup_templates', return_value=mock_templates), \
            patch('configs.cache_template.cache') as mock_cache:
        init_lookup_templates_cache()
        mock_cache.set.assert_called_once_with("lookup_templates",
                                               {template['name']: template['content'] for template in mock_templates})


def test_get_template_content_by_name():
    with app.app_context(), patch('configs.cache_template.cache') as mock_cache:
        mock_cache.get.return_value = {template['name']: template['content'] for template in mock_templates}

        template_content = get_template_content_by_name("no_match")
        assert template_content == "No match for {address}"

        template_content = get_template_content_by_name("wrong_format")
        assert template_content == "Wrong format"

        template_content = get_template_content_by_name("non_existent")
        assert template_content is None


def test_update_lookup_templates_cache():
    with patch('configs.cache_template.get_lookup_templates', return_value=mock_templates), \
            patch('configs.cache_template.cache') as mock_cache:
        update_lookup_templates_cache()
        mock_cache.set.assert_called_once_with("lookup_templates",
                                               {template['name']: template['content'] for template in mock_templates})


def test_get_tax_message():
    with patch('configs.cache_template.get_template_content_by_name') as mock_get_template:
        mock_get_template.side_effect = lambda name: f"Content for {name}" if name in ["has_tax_debt", "foreclosed",
                                                                                       "forfeited"] else None

        assert get_tax_message("TAX_DEBT") == "Content for has_tax_debt"
        assert get_tax_message("FORECLOSED") == "Content for foreclosed"
        assert get_tax_message("FORFEITED") == "Content for forfeited"
        assert get_tax_message("NO_INFORMATION") is None


def test_get_rental_message():
    with patch('configs.cache_template.get_template_content_by_name') as mock_get_template:
        mock_get_template.side_effect = lambda name: f"Content for {name}" if name in ["registered",
                                                                                       "unregistered"] else None

        assert get_rental_message("REGISTERED") == "Content for registered"
        assert get_rental_message("UNREGISTERED") == "Content for unregistered"
        assert get_rental_message("NO_INFORMATION") is None


def test_run_websocket_listener():
    with patch('configs.supabase.asyncio.new_event_loop') as mock_new_event_loop, \
            patch('configs.supabase.asyncio.set_event_loop') as mock_set_event_loop, \
            patch('configs.supabase.asyncio.get_event_loop') as mock_get_event_loop, \
            patch('configs.supabase.connect_to_supabase') as mock_connect_to_supabase:
        loop_mock = mock_new_event_loop.return_value
        run_websocket_listener()
        mock_connect_to_supabase.assert_called_once()
        loop_mock.run_forever.assert_called_once()