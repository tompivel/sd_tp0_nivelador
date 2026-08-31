import socket
import logger
from . import protocol
from lottery.lottery import Lottery

class Server:
    def __init__(self, server_host: str, server_port: int, storage_path: str) -> None:
        self.server_host = server_host
        self.server_port = server_port
        self.lottery = Lottery(storage_path)

    def _handle_client(self, client_socket):
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
                        
                    self.lottery.store_bets(bets)
                    protocol.send_message(client_socket, protocol.OP_BATCH_ACK, b'')
                    
                elif opcode == protocol.OP_END:
                    winners = []
                    # Find winners specifically for this agency
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
            raise e

    def run(self):
        action = "accept-connection"
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind((self.server_host, self.server_port))
            server_socket.listen()
            while True:
                try:
                    logger.info(action, logger.LogResult.in_progress)
                    client_socket, _ = server_socket.accept()
                except Exception as e:
                    logger.error(action, logger.LogResult.fail)
                    raise e
                logger.info(action, logger.LogResult.success)

                self._handle_client(client_socket)
