"""
Tests for txsftp.handler — GPGFileTransferServer event handlers.

GPGFileTransferServer.open() and close() are called directly rather than
through the full SFTP protocol stack, since the AbstractEventedFileTransferServer
wiring requires a live connection.
"""

import pytest
from unittest.mock import patch

from txsftp.handler import GPGFileTransferServer
from txsftp.server import FXF_WRITE, FXF_READ, FXF_CREAT, parse_flags


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_server():
    """Instantiate GPGFileTransferServer without invoking its broken __init__."""
    server = GPGFileTransferServer.__new__(GPGFileTransferServer)
    server.listeners = {}
    return server


def upload_data(filename):
    """Simulate an upload event data dict."""
    flags = parse_flags(FXF_WRITE | FXF_CREAT)
    return {'filename': filename, 'flags': flags}


def download_data(filename):
    """Simulate a download event data dict."""
    flags = parse_flags(FXF_READ)
    return {'filename': filename, 'flags': flags}


# ---------------------------------------------------------------------------
# GPGFileTransferServer.open()
# ---------------------------------------------------------------------------

def test_open_upload_logs(capsys):
    server = make_server()
    with patch('txsftp.handler.log') as mock_log:
        server.open('open', upload_data('data.gpg'))
    mock_log.msg.assert_called_once()
    assert 'upload' in mock_log.msg.call_args[0][0]
    assert 'data.gpg' in mock_log.msg.call_args[0][0]


def test_open_download_logs(capsys):
    server = make_server()
    with patch('txsftp.handler.log') as mock_log:
        server.open('open', download_data('report.txt'))
    mock_log.msg.assert_called_once()
    assert 'download' in mock_log.msg.call_args[0][0]
    assert 'report.txt' in mock_log.msg.call_args[0][0]


def test_open_any_extension_allowed():
    server = make_server()
    with patch('txsftp.handler.log'):
        server.open('open', upload_data('report.txt'))
        server.open('open', upload_data('data.gpg'))
        server.open('open', upload_data('message.pgp'))
        server.open('open', upload_data('archive.zip'))


# ---------------------------------------------------------------------------
# GPGFileTransferServer.close()
# ---------------------------------------------------------------------------

def test_close_upload_logs():
    server = make_server()
    with patch('txsftp.handler.log') as mock_log:
        server.close('close', upload_data('data.gpg'))
    mock_log.msg.assert_called_once()
    assert 'upload' in mock_log.msg.call_args[0][0]


def test_close_download_logs():
    server = make_server()
    with patch('txsftp.handler.log') as mock_log:
        server.close('close', download_data('data.txt'))
    mock_log.msg.assert_called_once()
    assert 'download' in mock_log.msg.call_args[0][0]


# ---------------------------------------------------------------------------
# getListenerDict
# ---------------------------------------------------------------------------

def test_get_listener_dict_keys():
    server = make_server()
    d = server.getListenerDict()
    assert 'open' in d
    assert 'close' in d
    assert d['open'] == server.open
    assert d['close'] == server.close
