"""
Tests for txsftp.auth — authentication checkers and SSH realm.
"""

import base64
import pytest
from unittest.mock import MagicMock, patch

from twisted.internet import defer
from twisted.cred import error as cred_error
from twisted.conch.error import ValidPublicKey

from txsftp.auth import (
    UsernamePasswordChecker,
    SSHKeyChecker,
    VirtualizedSSHRealm,
    VirtualizedConchUser,
)
from tests.conftest import TESTUSER_PASSWORD, TESTUSER_SSH_PUBLIC_KEY, TESTUSER_SSH_BLOB


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_password_creds(username, password):
    creds = MagicMock()
    creds.username = username if isinstance(username, bytes) else username.encode()
    creds.password = password if isinstance(password, bytes) else password.encode()
    return creds


def make_ssh_key_creds(username, blob=b'fake-blob', signature=b'fake-sig', sig_data=b'fake-data'):
    creds = MagicMock()
    creds.username = username if isinstance(username, bytes) else username.encode()
    creds.blob = blob
    creds.signature = signature
    creds.sigData = sig_data
    return creds


# ---------------------------------------------------------------------------
# UsernamePasswordChecker
# ---------------------------------------------------------------------------

@pytest.mark.twisted
def test_password_checker_valid_login(fake_db):
    checker = UsernamePasswordChecker(fake_db)
    creds = make_password_creds('testuser', TESTUSER_PASSWORD)

    d = checker.requestAvatarId(creds)

    @d.addCallback
    def check(result):
        assert result == 'testuser'

    return d


@pytest.mark.twisted
def test_password_checker_wrong_password(fake_db):
    checker = UsernamePasswordChecker(fake_db)
    creds = make_password_creds('testuser', 'wrongpass')

    d = checker.requestAvatarId(creds)
    d.addCallback(lambda r: pytest.fail("Should have raised UnauthorizedLogin"))
    d.addErrback(lambda f: f.trap(cred_error.UnauthorizedLogin))
    return d


@pytest.mark.twisted
def test_password_checker_unknown_user(fake_db):
    checker = UsernamePasswordChecker(fake_db)
    creds = make_password_creds('nobody', 'anything')

    d = checker.requestAvatarId(creds)
    d.addCallback(lambda r: pytest.fail("Should have raised UnauthorizedLogin"))
    d.addErrback(lambda f: f.trap(cred_error.UnauthorizedLogin))
    return d


@pytest.mark.twisted
def test_password_checker_decodes_bytes(fake_db):
    """Verify the DB is queried with a decoded str, not raw bytes."""
    checker = UsernamePasswordChecker(fake_db)
    creds = make_password_creds(b'testuser', TESTUSER_PASSWORD.encode())

    d = checker.requestAvatarId(creds)

    @d.addCallback
    def check(result):
        # The returned avatar ID must be a plain string, not bytes
        assert isinstance(result, str)
        call_args = fake_db.runQuery.call_args
        username_param = call_args[0][1][0]
        assert isinstance(username_param, str)

    return d


# ---------------------------------------------------------------------------
# SSHKeyChecker
# ---------------------------------------------------------------------------

@pytest.mark.twisted
def test_ssh_key_checker_no_signature(fake_db):
    """When no signature is present, ValidPublicKey should be raised."""
    checker = SSHKeyChecker(fake_db)
    creds = make_ssh_key_creds('testuser', signature=None)

    d = checker.requestAvatarId(creds)
    d.addCallback(lambda r: pytest.fail("Should have raised ValidPublicKey"))
    d.addErrback(lambda f: f.trap(ValidPublicKey))
    return d


@pytest.mark.twisted
def test_ssh_key_checker_valid_key(fake_db, sample_user_row):
    """A valid key + matching DB entry returns the username."""
    # Use the known blob from conftest — the sample_user_row key encodes this exact blob
    blob = TESTUSER_SSH_BLOB

    creds = make_ssh_key_creds('testuser', blob=blob)

    checker = SSHKeyChecker(fake_db)

    with patch('txsftp.auth.keys.Key') as MockKey:
        mock_key_instance = MagicMock()
        mock_key_instance.verify.return_value = True
        MockKey.fromString.return_value = mock_key_instance

        d = checker.requestAvatarId(creds)

        @d.addCallback
        def check(result):
            assert result == 'testuser'

        return d


@pytest.mark.twisted
def test_ssh_key_checker_unknown_user(fake_db):
    """Signature passes but no DB row → UnauthorizedLogin."""
    creds = make_ssh_key_creds('nobody')
    checker = SSHKeyChecker(fake_db)

    with patch('txsftp.auth.keys.Key') as MockKey:
        mock_key_instance = MagicMock()
        mock_key_instance.verify.return_value = True
        MockKey.fromString.return_value = mock_key_instance

        d = checker.requestAvatarId(creds)
        d.addCallback(lambda r: pytest.fail("Should have raised UnauthorizedLogin"))
        d.addErrback(lambda f: f.trap(cred_error.UnauthorizedLogin))
        return d


# ---------------------------------------------------------------------------
# VirtualizedSSHRealm
# ---------------------------------------------------------------------------

@pytest.mark.twisted
def test_realm_returns_virtualized_user(fake_db):
    """requestAvatar returns (interface, VirtualizedConchUser, logout)."""
    from twisted.conch.ssh import filetransfer
    from twisted.conch import interfaces as conch_ifaces

    realm = VirtualizedSSHRealm(fake_db)

    with patch('txsftp.auth.conf') as mock_conf, patch('txsftp.auth.os.makedirs'):
        mock_conf.get.return_value = 'default'
        d = realm.requestAvatar('testuser', None, conch_ifaces.IConchUser)

        @d.addCallback
        def check(result):
            iface, user, logout = result
            assert isinstance(user, VirtualizedConchUser)
            assert callable(logout)

        return d


@pytest.mark.twisted
def test_realm_decodes_bytes_username(fake_db):
    """Bytes username is decoded before the DB query."""
    from twisted.conch import interfaces as conch_ifaces

    realm = VirtualizedSSHRealm(fake_db)

    with patch('txsftp.auth.conf') as mock_conf, patch('txsftp.auth.os.makedirs'):
        mock_conf.get.return_value = 'default'
        d = realm.requestAvatar(b'testuser', None, conch_ifaces.IConchUser)

        @d.addCallback
        def check(result):
            iface, user, logout = result
            call_args = fake_db.runQuery.call_args
            username_param = call_args[0][1][0]
            assert isinstance(username_param, str)

        return d
