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

from zope.interface import implements

from twisted.conch import unix
from twisted.conch.ssh import filetransfer
from twisted.python.filepath import FilePath, InsecurePath
from twisted.conch.ssh.filetransfer import FXF_READ, FXF_WRITE, FXF_APPEND, FXF_CREAT, FXF_TRUNC, FXF_EXCL

UPLOAD_TYPES = (
	'write-only',
	'create',
)

DOWNLOAD_TYPES = (
	'read-only',
)

def detect_transfer_type(flags):
	if([x for x in flags if x in UPLOAD_TYPES]):
		return 'upload'
	elif([x for x in flags if x in DOWNLOAD_TYPES]):
		return 'download'
	else:
		raise RuntimeError('unexpected flagset: %s' % flags)

def parse_flags(flags):
	result = []
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
	def __init__(self, server, filename, flags, attrs):
		unix.UnixSFTPFile.__init__(self, server, filename, flags, attrs)
		self.filename = filename
		self.flags = parse_flags(flags)
		self.attrs = attrs
		self.server.handleEvent('open', dict(
			filename	= self.filename,
			flags		= self.flags,
			attrs		= self.attrs,
		))
	
	def close(self):
		unix.UnixSFTPFile.close(self)
		self.server.handleEvent('close', dict(
			filename	= self.filename,
			flags		= self.flags,
			attrs		= self.attrs,
		))
	
	def writeChunk(self, offset, data):
		unix.UnixSFTPFile.writeChunk(self, offset, data)
		self.server.handleEvent('writeChunk', dict(
			filename	= self.filename,
			offset		= offset,
			data		= data,
		))
	
	def readChunk(self, offset, length):
		result = unix.UnixSFTPFile.readChunk(self, offset, length)
		self.server.handleEvent('readChunk', dict(
			filename	= self.filename,
			offeset		= offset,
			length		= length,
		))
		return result

class AbstractEventedFileTransferServer(filetransfer.FileTransferServer):
	def __init__(self, data=None, avatar=None):
		filetransfer.FileTransferServer.__init__(self, data, avatar)
		for event, listener in self.getListenerDict().items():
			self.client.addListener(event, listener)
	
	def getListenerDict(self):
		raise NotImplementedError('AbstractEventedFileTransferServer::getListeners()')

class RestrictedSFTPServer:
	"""
	This is much like unix.SFTPServerForUnixConchUser, but:
		- doesn't allow any traversal above the home directory
		- uid/gid can't be set
		- symlinks cannot be made
	"""
	# TODO: This doesn't return friendly error messages to the client when
	#		restricted operations are attempted (they generally are sent as
	#		"Failure").

	implements(filetransfer.ISFTPServer)

	def __init__(self, avatar):
		self.listeners = {}
		self.avatar = avatar
		self.homedir = FilePath(self.avatar.getHomeDir())
		# Make the home dir if it doesn't already exist
		try:
			self.homedir.makedirs()
		except OSError, e:
			if e.errno != errno.EEXIST:
				raise

	def addListener(self, event, listener):
		self.listeners.setdefault(event, []).append(listener)

	def handleEvent(self, event, data):
		for listener in self.listeners.get(event, []):
			listener(event, data)

	def _childPath(self, path):
		if path.startswith('/'):
			path = '.' + path
		return self.homedir.preauthChild(path)

	def gotVersion(self, otherVersion, extData):
		# we don't support anything extra beyond standard SFTP
		return {}

	def extendedRequest(self, extendedName, extendedData):
		# We don't implement any extensions to SFTP.
		raise NotImplementedError
	
	def openFile(self, filename, flags, attrs):
		return EventedUnixSFTPFile(self, self._childPath(filename).path, flags, attrs)

	def removeFile(self, filename):
		self._childPath(filename).remove()

	def renameFile(self, oldpath, newpath):
		old = self._childPath(oldpath)
		new = self._childPath(newpath)
		os.rename(old.path, new.path)

	def makeDirectory(self, path, attrs):
		path = self._childPath(path).path
		os.mkdir(path)
		# XXX: self._setattrs(path)

	def removeDirectory(self, path):
		os.rmdir(self._childPath(path).path)

	def openDirectory(self, path):
		return unix.UnixSFTPDirectory(self, self._childPath(path).path)

	def _getAttrs(self, s):
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
			"atime" : s.st_atime,
			"mtime" : s.st_mtime
		}

	def getAttrs(self, path, followLinks):
		path = self._childPath(path).path
		if followLinks:
			statFunc = os.stat
		else:
			statFunc = os.lstat
		return self._getAttrs(statFunc(path))
	
	def setAttrs(self, path, attrs):
		path = self._childPath(path).path
		# We ignore the uid and gid attributes!
		# XXX: should we raise an error if they try to set them?
		if 'permissions' in attrs:
			os.chmod(path, attrs["permissions"])
		if 'atime' in attrs and 'mtime' in attrs:
			os.utime(path, (attrs["atime"], attrs["mtime"]))

	def readLink(self, path):
		path = self._childPath(path).path
		return os.readlink(path)

	def makeLink(self, linkPath, targetPath):
		# We disallow symlinks entirely.
		raise OSError, 'Permission denied'

	def realPath(self, path):
		path = self._childPath(path)
		# Make sure it really exists
		path.restat()

		# If it exists, it must be a real path, because we've disallowed
		# creating symlinks!  So, we can just return the path as-is (after
		# prefixing it with "." rather than self.homedir).
		return '.' + path.path[len(self.homedir.path):]
