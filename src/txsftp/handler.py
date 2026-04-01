from typing import Any

from txsftp import server
from twisted.python import log


class GPGFileTransferServer(server.AbstractEventedFileTransferServer):
    def getListenerDict(self) -> dict[str, Any]:
        return dict(
            open    = self.open,
            close   = self.close,
        )

    def open(self, event: str, data: dict[str, Any]) -> None:
        transfer_type = server.detect_transfer_type(data['flags'])
        log.msg(f"{transfer_type} opened: {data['filename']}")

    def close(self, event: str, data: dict[str, Any]) -> None:
        transfer_type = server.detect_transfer_type(data['flags'])
        log.msg(f"{transfer_type} closed: {data['filename']}")
