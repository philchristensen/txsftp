from txsftp import server
from twisted.python import log


class GPGFileTransferServer(server.AbstractEventedFileTransferServer):
	def getListenerDict(self):
		return dict(
			open	= self.open,
			close	= self.close,
		)

	def open(self, event, data):
		transfer_type = server.detect_transfer_type(data['flags'])
		log.msg(f"{transfer_type} opened: {data['filename']}")

	def close(self, event, data):
		transfer_type = server.detect_transfer_type(data['flags'])
		log.msg(f"{transfer_type} closed: {data['filename']}")
