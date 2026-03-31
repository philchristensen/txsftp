"""
Tests for txsftp.dbapi — URL parsing and ReplicatedConnectionPool routing.
"""

import pytest
from unittest.mock import MagicMock, patch

from txsftp.dbapi import URL, ReplicatedConnectionPool


# ---------------------------------------------------------------------------
# URL parsing
# ---------------------------------------------------------------------------

def test_url_parses_scheme():
    u = URL('psycopg://user:pass@host/dbname')
    assert u['scheme'] == 'psycopg'


def test_url_parses_legacy_psycopg2_scheme():
    u = URL('psycopg2://user:pass@host/dbname')
    assert u['scheme'] == 'psycopg2'


def test_url_parses_user_password():
    u = URL('psycopg://myuser:mysecret@dbhost/mydb')
    assert u['user'] == 'myuser'
    assert u['passwd'] == 'mysecret'
    assert u['host'] == 'dbhost'
    assert u['path'] == '/mydb'


def test_url_str_roundtrip():
    src = 'psycopg://txsftp:txsftp@localhost/txsftp'
    assert str(URL(src)) == src


def test_url_parses_port():
    u = URL('psycopg://user:pass@host:5433/db')
    assert u['port'] == '5433'


# ---------------------------------------------------------------------------
# ReplicatedConnectionPool — query routing
# ---------------------------------------------------------------------------

def make_mock_pool(name='pool'):
    pool = MagicMock()
    pool.connkw = {'host': name}
    return pool


def test_replicated_select_goes_to_slave():
    master = make_mock_pool('master')
    slave = make_mock_pool('slave')

    rp = ReplicatedConnectionPool(master, write_only_master=True)
    rp.add_slave(slave)

    result = rp.getPoolFor('SELECT * FROM sftp_user')
    assert result is slave


def test_replicated_insert_goes_to_master():
    master = make_mock_pool('master')
    slave = make_mock_pool('slave')

    rp = ReplicatedConnectionPool(master, write_only_master=True)
    rp.add_slave(slave)

    result = rp.getPoolFor('INSERT INTO sftp_user VALUES (...)')
    assert result is master


def test_replicated_update_goes_to_master():
    master = make_mock_pool('master')
    rp = ReplicatedConnectionPool(master, write_only_master=True)
    result = rp.getPoolFor('UPDATE sftp_user SET last_login = NOW()')
    assert result is master


def test_replicated_no_slaves_falls_back_to_master():
    master = make_mock_pool('master')
    rp = ReplicatedConnectionPool(master, write_only_master=True)
    # No slaves added → getSlave() returns master
    assert rp.getSlave() is master


def test_replicated_master_included_in_slaves_by_default():
    """When write_only_master=False (default), master is also a slave."""
    master = make_mock_pool('master')
    rp = ReplicatedConnectionPool(master)
    assert master in rp.slaves


def test_replicated_write_only_master_excluded_from_slaves():
    master = make_mock_pool('master')
    rp = ReplicatedConnectionPool(master, write_only_master=True)
    assert master not in rp.slaves


def test_replicated_add_slave_no_duplicates():
    master = make_mock_pool('master')
    slave = make_mock_pool('slave')
    rp = ReplicatedConnectionPool(master, write_only_master=True)
    rp.add_slave(slave)
    rp.add_slave(slave)  # second add should be a no-op
    assert rp.slaves.count(slave) == 1


def test_replicated_create_temporary_table_goes_to_slave():
    master = make_mock_pool('master')
    slave = make_mock_pool('slave')
    rp = ReplicatedConnectionPool(master, write_only_master=True)
    rp.add_slave(slave)
    result = rp.getPoolFor('CREATE TEMPORARY TABLE tmp AS SELECT 1')
    assert result is slave


# ---------------------------------------------------------------------------
# URL scheme validation in connect()
# ---------------------------------------------------------------------------

def test_connect_rejects_unsupported_scheme():
    from txsftp.dbapi import connect
    with pytest.raises(RuntimeError, match="Only psycopg"):
        connect('mysql://user:pass@host/db')


def test_connect_rejects_list_input():
    from txsftp.dbapi import connect
    with pytest.raises(ValueError, match="tuple"):
        connect(['psycopg://a:b@h/d', 'psycopg://a:b@h/d'])
