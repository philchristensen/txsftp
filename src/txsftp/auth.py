# txsftp
# Copyright (c) 2011 Phil Christensen
#
#
# See LICENSE for details

"""
Virtualized SFTP user support.
"""

import warnings, crypt, base64, binascii

from zope.interface import implements

from twisted.python import log
from twisted.internet import defer

from twisted.cred import portal, checkers, credentials, error
from twisted.conch import unix, avatar
from twisted.conch.error import ValidPublicKey
from twisted.conch.ssh import session, filetransfer, keys

class UsernamePasswordChecker(object):
	credentialInterfaces = (credentials.IUsernamePassword,)
	implements(checkers.ICredentialsChecker)
	
	def __init__(self, db):
		self.db = db
	
	@defer.inlineCallbacks
	def requestAvatarId(self, credentials):
		result = yield self.db.runQuery('SELECT * FROM sftp_user WHERE username = %s', [credentials.username])
		validate = lambda p: crypt.crypt(credentials.password, p[0:2]) == p
		if(result and validate(result[0]['password'])):
			defer.returnValue(credentials.username)
		raise error.UnauthorizedLogin('Invalid login.')

class SSHKeyChecker(object):
	"""
	Checker that authenticates against SSH keys in the database.
	"""
	
	credentialInterfaces = (credentials.ISSHPrivateKey,)
	implements(checkers.ICredentialsChecker)
	
	def __init__(self, db):
		self.db = db
	
	@defer.inlineCallbacks
	def requestAvatarId(self, credentials):
		if not credentials.signature:
			raise ValidPublicKey()
		
		if keys.Key.fromString(credentials.blob).verify(credentials.signature, credentials.sigData):
			result = yield self.db.runQuery('SELECT * FROM sftp_user WHERE username = %s', [credentials.username])
			try:
				if(base64.decodestring(result[0]['public_key'].split()[1]) == credentials.blob):
					defer.returnValue(credentials.username)
			except binascii.Error, e:
				log.err("Couldn't decode public_key on file for %s: %s" % (credentials.username, e))
				raise error.UnauthorizedLogin("invalid key")
		raise error.UnauthorizedLogin("unable to verify key")


class VirtualizedSSHRealm(unix.UnixSSHRealm):
	implements(portal.IRealm)
	
	def __init__(self, db):
		self.db = db
	
	def requestAvatar(self, username, mind, *interfaces):
		user = VirtualizedConchUser(username)
		return interfaces[0], user, user.logout

class VirtualizedConchUser(avatar.ConchUser):
	def __init__(self, username):
		avatar.ConchUser.__init__(self)
		self.username = username
		self.channelLookup.update({"session": session.SSHSession})
		self.subsystemLookup.update({"sftp": filetransfer.FileTransferServer})
	
	def getUserGroupId(self):
		raise RuntimeError('getUserGroupId not implemented')
	
	def getOtherGroups(self):
		raise RuntimeError('getOtherGroups not implemented')
	
	def getHomeDir(self):
		warnings.warn('getHomeDir not implemented')
		return '/Users/phil/Workspace/txsftp'
	
	def getShell(self):
		raise RuntimeError('getShell not implemented')
	
	def global_tcpip_forward(self, data):
		warnings.warn('global_tcpip_forward, not implemented')
		return 0
	
	def global_cancel_tcpip_forward(self, data):
		warnings.warn('global_cancel_tcpip_forward not implemented')
		return 0
	
	def logout(self):
		log.msg('avatar %s logging out' % self.username)
	
	def _runAsUser(self, f, *args, **kw):
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
