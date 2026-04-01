"""
Tests for txsftp.dbapi — URL conversion and TxPool async pool.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from txsftp.dbapi import _url_to_conninfo, connect, TxPool


def async_cm(return_value):
    """Build a MagicMock that acts as an async context manager yielding return_value."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=return_value)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


# ---------------------------------------------------------------------------
# URL conversion
# ---------------------------------------------------------------------------

def test_url_converts_psycopg_scheme():
    assert _url_to_conninfo('psycopg://user:pass@host/db') == 'postgresql://user:pass@host/db'


def test_url_converts_psycopg2_scheme():
    assert _url_to_conninfo('psycopg2://user:pass@host/db') == 'postgresql://user:pass@host/db'


def test_url_preserves_port():
    assert _url_to_conninfo('psycopg://user:pass@host:5433/db') == 'postgresql://user:pass@host:5433/db'


def test_url_preserves_credentials():
    result = _url_to_conninfo('psycopg://txsftp:txsftp@localhost/txsftp')
    assert result == 'postgresql://txsftp:txsftp@localhost/txsftp'


# ---------------------------------------------------------------------------
# Scheme validation
# ---------------------------------------------------------------------------

def test_connect_rejects_unsupported_scheme():
    with pytest.raises(RuntimeError, match="Only psycopg"):
        connect('mysql://user:pass@host/db')


def test_tx_pool_rejects_unsupported_scheme():
    with pytest.raises(RuntimeError, match="Only psycopg"):
        with patch('txsftp.dbapi.AsyncConnectionPool'):
            TxPool('mysql://user:pass@host/db')


# ---------------------------------------------------------------------------
# TxPool async methods
# ---------------------------------------------------------------------------

@pytest.fixture
def tx_pool(mocker):
    mock_pool_class = mocker.patch('txsftp.dbapi.AsyncConnectionPool')
    # open() is awaited via run_until_complete() in __init__ — must be a coroutine
    mock_pool_class.return_value.open = AsyncMock()
    # Provide a mock event loop so TxPool.__init__ doesn't need a real one
    mock_loop = MagicMock()
    mocker.patch('asyncio.get_event_loop', return_value=mock_loop)
    pool = TxPool('psycopg://user:pass@host/db')
    # connection() is called synchronously and returns an async CM — use MagicMock
    pool._pool = MagicMock()
    return pool


@pytest.mark.twisted
async def test_run_query_returns_list_of_dicts(tx_pool):
    """runQuery returns rows as a list of dicts."""
    expected = [{'id': 1, 'username': 'alice'}]
    mock_cur = AsyncMock()
    mock_cur.fetchall.return_value = expected
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = async_cm(mock_cur)
    tx_pool._pool.connection.return_value = async_cm(mock_conn)

    result = await tx_pool._run_query('SELECT * FROM sftp_user WHERE username = %s', ['alice'])

    assert result == expected
    mock_cur.execute.assert_awaited_once_with(
        'SELECT * FROM sftp_user WHERE username = %s', ['alice']
    )


@pytest.mark.twisted
async def test_run_operation_executes_query(tx_pool):
    """runOperation executes without returning rows."""
    mock_cur = AsyncMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = async_cm(mock_cur)
    tx_pool._pool.connection.return_value = async_cm(mock_conn)

    await tx_pool._run_operation(
        'INSERT INTO sftp_user (username) VALUES (%s)', ['bob']
    )

    mock_cur.execute.assert_awaited_once_with(
        'INSERT INTO sftp_user (username) VALUES (%s)', ['bob']
    )


@pytest.mark.twisted
async def test_run_interaction_passes_connection(tx_pool):
    """runInteraction passes the AsyncConnection to the callable."""
    mock_conn = AsyncMock()
    tx_pool._pool.connection.return_value = async_cm(mock_conn)

    async def my_interaction(conn):
        return 'result'

    result = await tx_pool._run_interaction(my_interaction)
    assert result == 'result'
