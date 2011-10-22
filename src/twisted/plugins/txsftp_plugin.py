# txsftp
# Copyright (c) 2011 Phil Christensen
#
#
# See LICENSE for details

"""
twistd plugin support

This module adds a 'txsftp' server type to the twistd service list.
"""

import os, warnings

from zope.interface import classProvides

from twisted import plugin
from twisted.python import usage, log
from twisted.internet import reactor
from twisted.application import internet, service

from twisted.conch.ssh import filetransfer
from twisted.conch.ssh.keys import Key
from twisted.conch.ssh.factory import SSHFactory
from twisted.conch import unix
from twisted.cred.portal import Portal

from txsftp import conf, auth, dbapi, server

from twisted.python import components
components.registerAdapter(server.RestrictedSFTPServer, auth.VirtualizedConchUser, filetransfer.ISFTPServer)

class txsftp_plugin(object):
	"""
	The txsftp application server startup class.
	"""

	classProvides(service.IServiceMaker, plugin.IPlugin)

	tapname = "txsftp"
	description = "Run a txsftp server."

	class options(usage.Options):
		"""
		Implement option-parsing for the txsftp twistd plugin.
		"""
		optParameters = [
			["conf", "f", "/etc/txsftp.json", "Path to configuration file, if any.", str],
		]

	@classmethod
	def makeService(cls, config):
		"""
		Create the txsftp service.
		"""
		if(conf.get('suppress-deprecation-warnings')):
			warnings.filterwarnings('ignore', r'.*', DeprecationWarning)
		
		get_key = lambda path: Key.fromString(data=open(path).read())
		ssh_public_key = get_key(conf.get('ssh-public-key'))
		ssh_private_key = get_key(conf.get('ssh-private-key'))

		factory = SSHFactory()
		factory.privateKeys = {'ssh-rsa': ssh_private_key}
		factory.publicKeys = {'ssh-rsa': ssh_public_key}

		db = dbapi.connect(conf.get('db-url'))
		factory.portal = Portal(auth.VirtualizedSSHRealm(db))
		factory.portal.registerChecker(auth.UsernamePasswordChecker(db))
		factory.portal.registerChecker(auth.SSHKeyChecker(db))

		return internet.TCPServer(conf.get('sftp-port'), factory)
