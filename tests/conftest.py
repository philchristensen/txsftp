"""
Shared pytest fixtures for the txsftp test suite.
"""

import base64
import os
import pytest
from unittest.mock import MagicMock
from passlib.hash import des_crypt

from twisted.internet import defer


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

TESTUSER_PASSWORD = 'testpass'
TESTUSER_PASSWORD_HASH = des_crypt.using(salt='hU').hash(TESTUSER_PASSWORD)

# A synthetic blob and matching public-key string with properly padded base64
TESTUSER_SSH_BLOB = b'fake-ssh-key-blob-for-testing-purposes'
TESTUSER_SSH_PUBLIC_KEY = (
    'ssh-rsa ' + base64.b64encode(TESTUSER_SSH_BLOB).decode() + ' testkey@localhost'
)


@pytest.fixture
def sample_user_row():
    """A dict matching the sftp_user schema with known credentials."""
    return {
        'id': 1,
        'username': 'testuser',
        'password': TESTUSER_PASSWORD_HASH,
        'gpg_public_key': None,
        'ssh_public_key': TESTUSER_SSH_PUBLIC_KEY,
        'home_directory': '/data/sftp/testuser',
        'last_login': None,
        'last_logout': None,
    }


@pytest.fixture
def fake_db(sample_user_row):
    """
    A mock database pool.  runQuery returns a Deferred that fires with
    a list containing the sample_user_row, or an empty list if the
    username doesn't match.
    """
    db = MagicMock()

    def _run_query(query, params):
        username = params[0] if params else None
        if username == 'testuser':
            return defer.succeed([sample_user_row])
        return defer.succeed([])

    db.runQuery.side_effect = _run_query
    db.runOperation.return_value = defer.succeed(None)
    return db


@pytest.fixture
def tmp_homedir(tmp_path):
    """A real temporary directory to use as a user home directory."""
    homedir = tmp_path / 'home'
    homedir.mkdir()
    return str(homedir)


@pytest.fixture
def restricted_server(tmp_homedir):
    """
    A RestrictedSFTPServer instance with a minimal avatar pointing at
    tmp_homedir.
    """
    from txsftp.server import RestrictedSFTPServer

    avatar = MagicMock()
    avatar.getHomeDir.return_value = tmp_homedir

    return RestrictedSFTPServer(avatar)
