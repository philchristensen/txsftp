# txsftp
# Copyright (c) 2011 Phil Christensen
# Copyright (c) 2005 Canonical Ltd.
#
# See LICENSE for details

"""
A restricted chroot-like SFTP backend.

It presents the user with a virtual filesystem rooted at their home directory,
and they can't break out of it.
"""
import os, errno
from typing import Any, Callable

from zope.interface import implementer

from twisted.conch import unix
from twisted.conch.ssh import filetransfer
from twisted.python.filepath import FilePath
from twisted.conch.ssh.filetransfer import FXF_READ, FXF_WRITE, FXF_APPEND, FXF_CREAT, FXF_TRUNC, FXF_EXCL

UPLOAD_TYPES = (
    'write-only',
    'create',
)

DOWNLOAD_TYPES = (
    'read-only',
)

def detect_transfer_type(flags: list[str]) -> str:
    if([x for x in flags if x in UPLOAD_TYPES]):
        return 'upload'
    elif([x for x in flags if x in DOWNLOAD_TYPES]):
        return 'download'
    else:
        raise RuntimeError('unexpected flagset: %s' % flags)

def parse_flags(flags: int) -> list[str]:
    result: list[str] = []
    if flags & FXF_READ == FXF_READ and flags & FXF_WRITE == 0:
        result.append('read-only')
    if flags & FXF_WRITE == FXF_WRITE and flags & FXF_READ == 0:
        result.append('write-only')
    if flags & FXF_WRITE == FXF_WRITE and flags & FXF_READ == FXF_READ:
        result.append('read-write')
    if flags & FXF_APPEND == FXF_APPEND:
        result.append('append')
    if flags & FXF_CREAT == FXF_CREAT:
        result.append('create')
    if flags & FXF_TRUNC == FXF_TRUNC:
        result.append('truncate')
    if flags & FXF_EXCL == FXF_EXCL:
        result.append('exclusive')
    return result

class EventedUnixSFTPFile(unix.UnixSFTPFile):
    """
    Detect events and notify the server.
    """
    def __init__(self, server: Any, filename: str, flags: int, attrs: dict[str, Any]) -> None:
        unix.UnixSFTPFile.__init__(self, server, filename, flags, attrs)
        self.filename = filename
        self.flags = parse_flags(flags)
        self.attrs = attrs
        self.server.handleEvent('open', dict(
            filename    = self.filename,
            flags       = self.flags,
            attrs       = self.attrs,
        ))

    def close(self) -> None:
        unix.UnixSFTPFile.close(self)
        self.server.handleEvent('close', dict(
            filename    = self.filename,
            flags       = self.flags,
            attrs       = self.attrs,
        ))

    def writeChunk(self, offset: int, data: bytes) -> None:
        unix.UnixSFTPFile.writeChunk(self, offset, data)
        self.server.handleEvent('writeChunk', dict(
            filename    = self.filename,
            offset      = offset,
            data        = data,
        ))

    def readChunk(self, offset: int, length: int) -> bytes:
        result = unix.UnixSFTPFile.readChunk(self, offset, length)
        self.server.handleEvent('readChunk', dict(
            filename    = self.filename,
            offeset     = offset,
            length      = length,
        ))
        return result

class AbstractEventedFileTransferServer(filetransfer.FileTransferServer):
    def __init__(self, data=None, avatar=None):
        filetransfer.FileTransferServer.__init__(self, data, avatar)
        for event, listener in self.getListenerDict().items():
            self.client.addListener(event, listener)

    def getListenerDict(self):
        raise NotImplementedError('AbstractEventedFileTransferServer::getListeners()')

@implementer(filetransfer.ISFTPServer)
class RestrictedSFTPServer:
    """
    This is much like unix.SFTPServerForUnixConchUser, but:
        - doesn't allow any traversal above the home directory
        - uid/gid can't be set
        - symlinks cannot be made
    """
    # TODO: This doesn't return friendly error messages to the client when
    #       restricted operations are attempted (they generally are sent as
    #       "Failure").

    def __init__(self, avatar):
        self.listeners = {}
        self.avatar = avatar
        self.homedir = FilePath(self.avatar.getHomeDir())
        # Make the home dir if it doesn't already exist
        try:
            self.homedir.makedirs()
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    def addListener(self, event: str, listener: Any) -> None:
        self.listeners.setdefault(event, []).append(listener)

    def handleEvent(self, event: str, data: dict[str, Any]) -> None:
        for listener in self.listeners.get(event, []):
            listener(event, data)

    def _childPath(self, path: str | bytes) -> FilePath:
        if isinstance(path, bytes):
            path = path.decode('utf-8')
        if path.startswith('/'):
            path = '.' + path
        result = self.homedir.preauthChild(path)
        return result

    def gotVersion(self, otherVersion: int, extData: dict[str, Any]) -> dict[str, Any]:
        # we don't support anything extra beyond standard SFTP
        return {}

    def extendedRequest(self, extendedName: str, extendedData: bytes) -> bytes:
        # We don't implement any extensions to SFTP.
        raise NotImplementedError

    def openFile(self, filename: str | bytes, flags: int, attrs: dict[str, Any]) -> EventedUnixSFTPFile:
        return EventedUnixSFTPFile(self, self._childPath(filename).path, flags, attrs)

    def removeFile(self, filename: str | bytes) -> None:
        self._childPath(filename).remove()

    def renameFile(self, oldpath: str | bytes, newpath: str | bytes) -> None:
        old = self._childPath(oldpath)
        new = self._childPath(newpath)
        os.rename(old.path, new.path)

    def makeDirectory(self, path: str | bytes, attrs: dict[str, Any]) -> None:
        path = self._childPath(path).path
        os.mkdir(path)
        # XXX: self._setattrs(path)

    def removeDirectory(self, path: str | bytes) -> None:
        os.rmdir(self._childPath(path).path)

    def openDirectory(self, path: str | bytes) -> unix.UnixSFTPDirectory:
        return unix.UnixSFTPDirectory(self, self._childPath(path).path)

    def _getAttrs(self, s: os.stat_result) -> dict[str, int]:
        """Convert the result of os.stat/os.lstat to an SFTP attributes dict

        Ideally this would be named something more like _statToAttrs, but this
        is required by UnixSFTPDirectory.
        """
        # FIXME: We probably want to give fake uid/gid details.
        # From twisted.conch.unix.SFTPServerForUnixConchUser._getAttrs
        return {
            "size" : s.st_size,
            "uid" : s.st_uid,
            "gid" : s.st_gid,
            "permissions" : s.st_mode,
            "atime" : int(s.st_atime),
            "mtime" : int(s.st_mtime)
        }

    def getAttrs(self, path: str | bytes, followLinks: bool) -> dict[str, int]:
        resolved = self._childPath(path).path
        statFunc: Callable[[str], os.stat_result] = os.stat if followLinks else os.lstat
        if("\x00" in resolved):
            resolved, _garbage = resolved.split("\x00", 1)
        return self._getAttrs(statFunc(resolved))

    def setAttrs(self, path: str | bytes, attrs: dict[str, Any]) -> None:
        path = self._childPath(path).path
        # We ignore the uid and gid attributes!
        # XXX: should we raise an error if they try to set them?
        if 'permissions' in attrs:
            os.chmod(path, attrs["permissions"])
        if 'atime' in attrs and 'mtime' in attrs:
            os.utime(path, (attrs["atime"], attrs["mtime"]))

    def readLink(self, path: str | bytes) -> str:
        resolved: str = self._childPath(path).path
        return os.readlink(resolved)

    def makeLink(self, linkPath: str | bytes, targetPath: str | bytes) -> None:
        # We disallow symlinks entirely.
        raise OSError('Permission denied')

    def realPath(self, path: str | bytes) -> str:
        fp = self._childPath(path)
        # Make sure it really exists
        fp.restat()

        # If it exists, it must be a real path, because we've disallowed
        # creating symlinks!  So, we can just return the path as-is (after
        # prefixing it with "." rather than self.homedir).
        new_path = fp.path[len(self.homedir.path):]
        if(new_path == ''):
            return '/'
        return '.' + new_path
