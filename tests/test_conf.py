"""
Tests for txsftp.conf — configuration loading and merging.
"""

import json
import os
import pytest
import txsftp.conf as conf_module
from txsftp.conf import read_config, _read_config, get


@pytest.fixture(autouse=True)
def reset_config(monkeypatch):
    """Reset the module-level config cache before each test."""
    monkeypatch.setattr(conf_module, 'config', None)


# ---------------------------------------------------------------------------
# read_config — default.json is always loaded
# ---------------------------------------------------------------------------

def test_loads_default_config():
    """read_config always returns a dict with keys from default.json."""
    result = read_config('/nonexistent/path/to/txsftp.json')
    assert isinstance(result, dict)
    assert 'sftp-port' in result
    assert result['sftp-port'] == 8888


def test_default_db_url_uses_psycopg_scheme():
    result = read_config('/nonexistent')
    assert result['db-url'].startswith('psycopg://')


# ---------------------------------------------------------------------------
# read_config — system config file override
# ---------------------------------------------------------------------------

def test_system_conf_overrides(tmp_path):
    """Values from a system config file override defaults."""
    override = tmp_path / 'txsftp.json'
    override.write_text(json.dumps({'sftp-port': 9999}))

    result = read_config(str(override))
    assert result['sftp-port'] == 9999
    # Other default keys should still be present
    assert 'db-url' in result


def test_system_conf_adds_new_keys(tmp_path):
    override = tmp_path / 'txsftp.json'
    override.write_text(json.dumps({'custom-key': 'custom-value'}))

    result = read_config(str(override))
    assert result['custom-key'] == 'custom-value'
    assert result['sftp-port'] == 8888  # default still present


# ---------------------------------------------------------------------------
# _read_config — error handling
# ---------------------------------------------------------------------------

def test_invalid_json_raises_syntax_error(tmp_path):
    bad_file = tmp_path / 'bad.json'
    bad_file.write_text('{not valid json')

    with pytest.raises(SyntaxError, match='config parse error'):
        with open(bad_file) as f:
            _read_config(f)


def test_non_dict_json_raises_syntax_error(tmp_path):
    arr_file = tmp_path / 'arr.json'
    arr_file.write_text('[1, 2, 3]')

    with pytest.raises(SyntaxError, match="single top-level object"):
        with open(arr_file) as f:
            _read_config(f)


# ---------------------------------------------------------------------------
# get() — reads from cached config
# ---------------------------------------------------------------------------

def test_get_returns_value(tmp_path):
    """get() returns the correct value after priming the cache via load()."""
    override = tmp_path / 'txsftp.json'
    override.write_text(json.dumps({'sftp-port': 7777}))

    # Prime the cache with our override file, then get() uses the cached result
    import txsftp.conf as conf_mod
    conf_mod.load(str(override))
    result = get('sftp-port')
    assert result == 7777


def test_get_caches_after_first_load(tmp_path):
    """Calling get() twice returns the value from the first load, not the file."""
    override = tmp_path / 'txsftp.json'
    override.write_text(json.dumps({'sftp-port': 6666}))

    import txsftp.conf as conf_mod
    conf_mod.load(str(override))
    # Overwrite the file — the cached value should still be returned
    override.write_text(json.dumps({'sftp-port': 5555}))
    result = get('sftp-port')
    assert result == 6666  # still the cached value
