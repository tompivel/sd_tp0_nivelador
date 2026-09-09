import signal
import socket
import threading
from dataclasses import dataclass
from typing import Any, List, Optional

import logger
import utils.rwlock
from lottery.lottery import Lottery

from . import protocol


@dataclass
class ServerConfig:
    server_host: str
    server_port: int
    storage_path: str
    agency_quorum_min: int


class GracefulExit(Exception):
    pass


class Server:
    def __init__(
        self,
        config: ServerConfig,
    ) -> None:
        self.server_host = config.server_host
        self.server_port = config.server_port
        self.lottery = Lottery(config.storage_path)
        self.agency_quorum_min = config.agency_quorum_min
        self.rwlock = utils.rwlock.RWLock()
        self.socket_lock = threading.Lock()
        self.draw_barrier = threading.Barrier(self.agency_quorum_min)
        self.active_sockets: List[socket.socket] = []

        # Register the signal handler
        signal.signal(signal.SIGTERM, self.handle_sigterm)

    def handle_sigterm(self, signum: int, frame: Any) -> None:
        raise GracefulExit()

    def _handle_batch(self, client_socket: socket.socket, payload: bytes, agency_id: Optional[int]) -> Optional[int]:
        batch = protocol.deserialize_batch(payload)
        
        if agency_id is None:
            agency_id = batch.agency_id
        elif agency_id != batch.agency_id:
            raise ValueError("Agency ID changed during session")

        with self.rwlock.write_lock():
            self.lottery.store_bets(batch.bets)

        protocol.send_message(client_socket, protocol.OpCode.BATCH_ACK, b"")
        return agency_id

    def _handle_end(self, client_socket: socket.socket, agency_id: Optional[int]) -> None:
        try:
            self.draw_barrier.wait()
        except threading.BrokenBarrierError:
            pass

        winners = []
        # Find winners specifically for this agency
        with self.rwlock.read_lock():
            for bet in self.lottery.load_bets():
                if bet.agency_id == agency_id and self.lottery.has_won(bet):
                    winners.append(bet)

        # Serialize winners
        winners_batch = protocol.Batch(agency_id=agency_id, bets=winners)
        winners_payload = protocol.serialize_batch(winners_batch)

        protocol.send_message(
            client_socket, protocol.OpCode.WINNERS, winners_payload
        )

    def _handle_client(self, client_socket: socket.socket) -> None:
        with self.socket_lock:
            self.active_sockets.append(client_socket)
        action = "handle-client"
        try:
            logger.info(action, logger.LogResult.in_progress)
            agency_id = None

            while True:
                opcode, payload = protocol.recv_message(client_socket)
                if not opcode:
                    break

                if opcode == protocol.OpCode.BATCH:
                    agency_id = self._handle_batch(client_socket, payload, agency_id)
                elif opcode == protocol.OpCode.END:
                    self._handle_end(client_socket, agency_id)
                    break

            logger.info(action, logger.LogResult.success)
        except Exception as e:
            logger.error(action, logger.LogResult.fail, "err", str(e))
        finally:
            client_socket.close()
            with self.socket_lock:
                if client_socket in self.active_sockets:
                    self.active_sockets.remove(client_socket)

    def run(self) -> None:
        action = "accept-connection"
        threads: List[threading.Thread] = []

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind((self.server_host, self.server_port))
            server_socket.listen()
            try:
                while True:
                    logger.info(action, logger.LogResult.in_progress)
                    client_socket, _ = server_socket.accept()
                    logger.info(action, logger.LogResult.success)

                    client_thread = threading.Thread(
                        target=self._handle_client, args=(client_socket,)
                    )
                    client_thread.start()
                    threads.append(client_thread)

            except GracefulExit:
                logger.info(
                    "server",
                    logger.LogResult.success,
                    "SIGTERM received. Aborting barrier and closing sockets.",
                )
                self.draw_barrier.abort()

                # Shutdown active sockets to unblock any pending recv() in client threads
                with self.socket_lock:
                    sockets_to_close = list(self.active_sockets)
                for sock in sockets_to_close:
                    try:
                        sock.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass

        for t in threads:
            t.join()
