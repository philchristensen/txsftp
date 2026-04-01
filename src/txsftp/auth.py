# txsftp
# Copyright (c) 2011 Phil Christensen
#
#
# See LICENSE for details

"""
Virtualized SFTP user support.
"""

import os, warnings, base64, binascii
from typing import Any

from zope.interface import implementer

from passlib.hash import des_crypt

from twisted.python import log, reflect
from twisted.internet import defer

from twisted.cred import portal, checkers, credentials, error
from twisted.conch import unix, avatar
from twisted.conch.error import ValidPublicKey
from twisted.conch.ssh import session, filetransfer, keys

from txsftp import conf


@implementer(checkers.ICredentialsChecker)
class UsernamePasswordChecker:
    credentialInterfaces = (credentials.IUsernamePassword,)

    def __init__(self, db: Any) -> None:
        self.db = db

    @defer.inlineCallbacks
    def requestAvatarId(self, credentials: Any) -> Any:
        username = credentials.username
        if isinstance(username, bytes):
            username = username.decode('utf-8')
        password = credentials.password
        if isinstance(password, bytes):
            password = password.decode('utf-8')
        result = yield self.db.runQuery(
            'SELECT * FROM sftp_user WHERE username = %s', [username]
        )
        if not result:
            raise error.UnauthorizedLogin('Invalid login.')
        stored_hash = result[0]['password']
        if stored_hash and des_crypt.verify(password, stored_hash):
            return username
        raise error.UnauthorizedLogin('Invalid login.')


@implementer(checkers.ICredentialsChecker)
class SSHKeyChecker:
    """
    Checker that authenticates against SSH keys in the database.
    """

    credentialInterfaces = (credentials.ISSHPrivateKey,)

    def __init__(self, db: Any) -> None:
        self.db = db

    @defer.inlineCallbacks
    def requestAvatarId(self, credentials: Any) -> Any:
        if not credentials.signature:
            raise ValidPublicKey()

        if keys.Key.fromString(credentials.blob).verify(credentials.signature, credentials.sigData):
            username = credentials.username
            if isinstance(username, bytes):
                username = username.decode('utf-8')
            result = yield self.db.runQuery(
                'SELECT * FROM sftp_user WHERE username = %s', [username]
            )
            if not result:
                raise error.UnauthorizedLogin('Invalid login.')
            try:
                stored_key = result[0]['ssh_public_key']
                if not stored_key:
                    raise error.UnauthorizedLogin("no SSH key on file")
                stored_key_b64 = stored_key.split()[1]
                if base64.decodebytes(stored_key_b64.encode('ascii')) == credentials.blob:
                    return username
            except binascii.Error as e:
                log.err("Couldn't decode ssh_public_key on file for %s: %s" % (username, e))
                raise error.UnauthorizedLogin("invalid key")
        raise error.UnauthorizedLogin("unable to verify key")


@implementer(portal.IRealm)
class VirtualizedSSHRealm(unix.UnixSSHRealm):
    def __init__(self, db: Any) -> None:
        self.db = db

    @defer.inlineCallbacks
    def requestAvatar(self, username: Any, mind: Any, *interfaces: Any) -> Any:  # type: ignore[override]
        if isinstance(username, bytes):
            username = username.decode('utf-8')
        result = yield self.db.runQuery(
            'SELECT * FROM sftp_user WHERE username = %s', [username]
        )
        user = VirtualizedConchUser(self.db, **result[0])
        os.makedirs(user.getHomeDir(), exist_ok=True)
        yield self.db.runOperation(
            'UPDATE sftp_user SET last_login = NOW() WHERE username = %s', [username]
        )
        return (interfaces[0], user, user.logout)


class VirtualizedConchUser(avatar.ConchUser):
    def __init__(self, db: Any, **attribs: Any) -> None:
        avatar.ConchUser.__init__(self)
        self.db = db
        self.attribs = attribs
        self.channelLookup.update({b"session": session.SSHSession})

        server_class = conf.get('server-class')
        if(server_class and server_class != 'default'):
            server_class = reflect.namedAny(server_class)
            self.subsystemLookup.update({b"sftp": server_class})
        else:
            self.subsystemLookup.update({b"sftp": filetransfer.FileTransferServer})

    def getUserGroupId(self) -> tuple[int, int]:
        raise RuntimeError('getUserGroupId not implemented')

    def getOtherGroups(self) -> list[int]:
        raise RuntimeError('getOtherGroups not implemented')

    def getHomeDir(self) -> str:
        return self.attribs['home_directory']

    def getShell(self) -> str:
        raise RuntimeError('getShell not implemented')

    def global_tcpip_forward(self, data: bytes) -> int:
        return 0

    def global_cancel_tcpip_forward(self, data: bytes) -> int:
        return 0

    def logout(self) -> Any:
        log.msg('avatar %s logging out' % self.attribs['username'])
        return self.db.runOperation(
            'UPDATE sftp_user SET last_logout = NOW() WHERE username = %s',
            [self.attribs['username']],
        )

    def _runAsUser(self, f: Any, *args: Any, **kw: Any) -> Any:
        warnings.warn('_runAsUser not implemented')
        try:
            f = iter(f)
        except TypeError:
            f = [(f, args, kw)]
        try:
            for i in f:
                func = i[0]
                args = len(i)>1 and i[1] or ()
                kw = len(i)>2 and i[2] or {}
                r = func(*args, **kw)
        finally:
            pass
        return r
