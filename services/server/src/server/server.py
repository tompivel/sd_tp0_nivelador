import socket
import threading
import signal
import logger
from . import protocol
from lottery.lottery import Lottery

class GracefulExit(Exception):
    pass

class Server:
    def __init__(self, server_host: str, server_port: int, storage_path: str, agency_quorum_min: int) -> None:
        self.server_host = server_host
        self.server_port = server_port
        self.lottery = Lottery(storage_path)
        self.agency_quorum_min = agency_quorum_min
        self.file_lock = threading.Lock()
        self.draw_barrier = threading.Barrier(self.agency_quorum_min)
        self.active_sockets = []
        
        # Register the signal handler
        signal.signal(signal.SIGTERM, self.handle_sigterm)

    def handle_sigterm(self, signum, frame):
        raise GracefulExit()

    def _handle_client(self, client_socket):
        self.active_sockets.append(client_socket)
        action = "handle-client"
        try:
            logger.info(action, logger.LogResult.in_progress)
            agency_id = None
            
            while True:
                opcode, payload = protocol.recv_message(client_socket)
                if not opcode:
                    break
                    
                if opcode == protocol.OP_BATCH:
                    bets = []
                    offset = 0
                    while offset < len(payload):
                        bet, offset = protocol.deserialize_bet(payload, offset)
                        bets.append(bet)
                        agency_id = bet.agency_id # Assume all bets in a connection belong to the same agency
                        
                    with self.file_lock:
                        self.lottery.store_bets(bets)
                    
                    protocol.send_message(client_socket, protocol.OP_BATCH_ACK, b'')
                    
                elif opcode == protocol.OP_END:
                    try:
                        self.draw_barrier.wait()
                    except threading.BrokenBarrierError:
                        pass
                        
                    winners = []
                    # Find winners specifically for this agency
                    with self.file_lock:
                        for bet in self.lottery.load_bets():
                            if bet.agency_id == agency_id and self.lottery.has_won(bet):
                                winners.append(bet)
                    
                    # Serialize winners
                    winners_payload = bytearray()
                    for winner in winners:
                        winners_payload.extend(protocol.serialize_bet(winner))
                        
                    protocol.send_message(client_socket, protocol.OP_WINNERS, bytes(winners_payload))
                    break
                    
            logger.info(action, logger.LogResult.success)
        except Exception as e:
            logger.error(action, logger.LogResult.fail, "err", str(e))
        finally:
            client_socket.close()
            if client_socket in self.active_sockets:
                self.active_sockets.remove(client_socket)

    def run(self):
        action = "accept-connection"
        threads = []
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind((self.server_host, self.server_port))
            server_socket.listen()
            try:
                while True:
                    logger.info(action, logger.LogResult.in_progress)
                    client_socket, _ = server_socket.accept()
                    logger.info(action, logger.LogResult.success)

                    client_thread = threading.Thread(target=self._handle_client, args=(client_socket,))
                    client_thread.start()
                    threads.append(client_thread)
            
            except GracefulExit:
                logger.info("server", logger.LogResult.success, "SIGTERM received. Aborting barrier and closing sockets.")
                self.draw_barrier.abort()
                
                # Shutdown active sockets to unblock any pending recv() in client threads
                for sock in self.active_sockets:
                    try:
                        sock.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                        
        for t in threads:
            t.join()
