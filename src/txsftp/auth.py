# txsftp
# Copyright (c) 2011 Phil Christensen
#
#
# See LICENSE for details

"""
Virtualized SFTP user support.
"""

import warnings

from zope.interface import implements

from twisted.python import log

from twisted.cred import portal, checkers, credentials
from twisted.conch import unix, avatar
from twisted.conch.ssh import session, filetransfer

class Checker(object):
	credentialInterfaces = (credentials.IUsernamePassword,)
	implements(checkers.ICredentialsChecker)
	
	def __init__(self, db):
		self.db = db
	
	def requestAvatarId(self, credentials):
		return credentials.username

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
