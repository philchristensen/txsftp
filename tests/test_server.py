"""
Tests for txsftp.server — RestrictedSFTPServer and helpers.
"""

import os
import pytest
from unittest.mock import MagicMock

from twisted.python.filepath import InsecurePath

from txsftp.server import (
    RestrictedSFTPServer,
    parse_flags,
    detect_transfer_type,
)
from twisted.conch.ssh.filetransfer import FXF_READ, FXF_WRITE, FXF_CREAT


# ---------------------------------------------------------------------------
# parse_flags / detect_transfer_type helpers
# ---------------------------------------------------------------------------

def test_parse_flags_read_only():
    assert 'read-only' in parse_flags(FXF_READ)


def test_parse_flags_write_only():
    assert 'write-only' in parse_flags(FXF_WRITE)


def test_parse_flags_create():
    assert 'create' in parse_flags(FXF_CREAT)


def test_detect_upload():
    assert detect_transfer_type(['write-only']) == 'upload'
    assert detect_transfer_type(['create']) == 'upload'


def test_detect_download():
    assert detect_transfer_type(['read-only']) == 'download'


def test_detect_unexpected_flagset():
    with pytest.raises(RuntimeError):
        detect_transfer_type(['append'])


# ---------------------------------------------------------------------------
# RestrictedSFTPServer — path restriction
# ---------------------------------------------------------------------------

def test_child_path_within_home(restricted_server, tmp_homedir):
    result = restricted_server._childPath('subdir/file.txt')
    assert result.path.startswith(tmp_homedir)
    assert result.path.endswith('file.txt')


def test_child_path_leading_slash_stripped(restricted_server, tmp_homedir):
    with_slash = restricted_server._childPath('/foo')
    without_slash = restricted_server._childPath('foo')
    assert with_slash.path == without_slash.path


def test_child_path_traversal_blocked(restricted_server):
    with pytest.raises(InsecurePath):
        restricted_server._childPath('../escape')


# ---------------------------------------------------------------------------
# RestrictedSFTPServer — symlink ban
# ---------------------------------------------------------------------------

def test_make_link_raises(restricted_server):
    with pytest.raises(OSError):
        restricted_server.makeLink('link', 'target')


# ---------------------------------------------------------------------------
# RestrictedSFTPServer — realPath
# ---------------------------------------------------------------------------

def test_real_path_home_is_slash(restricted_server, tmp_homedir):
    # The home dir itself already exists; realPath('.') should return '/'
    result = restricted_server.realPath('.')
    assert result == '/'


def test_real_path_subdir(restricted_server, tmp_homedir):
    subdir = os.path.join(tmp_homedir, 'mydir')
    os.mkdir(subdir)
    result = restricted_server.realPath('mydir')
    assert result == './mydir'


# ---------------------------------------------------------------------------
# RestrictedSFTPServer — event listener
# ---------------------------------------------------------------------------

def test_add_and_handle_event(restricted_server):
    received = []
    restricted_server.addListener('open', lambda event, data: received.append((event, data)))
    restricted_server.handleEvent('open', {'filename': 'test.gpg'})
    assert len(received) == 1
    assert received[0] == ('open', {'filename': 'test.gpg'})


def test_handle_event_no_listeners(restricted_server):
    # Should not raise even with no listeners registered
    restricted_server.handleEvent('open', {})


def test_multiple_listeners_for_same_event(restricted_server):
    calls = []
    restricted_server.addListener('close', lambda e, d: calls.append(1))
    restricted_server.addListener('close', lambda e, d: calls.append(2))
    restricted_server.handleEvent('close', {})
    assert calls == [1, 2]


# ---------------------------------------------------------------------------
# RestrictedSFTPServer — filesystem operations
# ---------------------------------------------------------------------------

def test_make_directory_creates_dir(restricted_server, tmp_homedir):
    restricted_server.makeDirectory('newdir', {})
    assert os.path.isdir(os.path.join(tmp_homedir, 'newdir'))


def test_remove_file(restricted_server, tmp_homedir):
    filepath = os.path.join(tmp_homedir, 'todelete.txt')
    open(filepath, 'w').close()
    restricted_server.removeFile('todelete.txt')
    assert not os.path.exists(filepath)


def test_remove_directory(restricted_server, tmp_homedir):
    dirpath = os.path.join(tmp_homedir, 'emptydir')
    os.mkdir(dirpath)
    restricted_server.removeDirectory('emptydir')
    assert not os.path.exists(dirpath)


def test_rename_file(restricted_server, tmp_homedir):
    src = os.path.join(tmp_homedir, 'before.txt')
    open(src, 'w').close()
    restricted_server.renameFile('before.txt', 'after.txt')
    assert not os.path.exists(src)
    assert os.path.exists(os.path.join(tmp_homedir, 'after.txt'))


def test_get_attrs_returns_stat_dict(restricted_server, tmp_homedir):
    filepath = os.path.join(tmp_homedir, 'statme.txt')
    open(filepath, 'w').close()
    attrs = restricted_server.getAttrs('statme.txt', followLinks=True)
    assert 'size' in attrs
    assert 'permissions' in attrs
    assert 'atime' in attrs
    assert 'mtime' in attrs
