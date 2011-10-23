from txsftp import server
from twisted.conch.ssh import filetransfer

class GPGFileTransferServer(server.AbstractEventedFileTransferServer):
	def getListenerDict(self):
		return dict(
			open	= self.open,
			close	= self.close,
		)
	
	def open(self, event, data):
		transfer_type = server.detect_transfer_type(data['flags'])
		if(transfer_type == 'upload'):
			if not(data['filename'].endswith('gpg') or data['filename'].endswith('pgp')):
				raise filetransfer.SFTPError(filetransfer.FX_OP_UNSUPPORTED, "Uploaded files *must* be GPG/PGP-encrypted")
		else:
			print 'download'
	
	def close(self, event, data):
		transfer_type = server.detect_transfer_type(data['flags'])
		if(transfer_type == 'upload'):
			print 'upload'
		else:
			print 'download'
