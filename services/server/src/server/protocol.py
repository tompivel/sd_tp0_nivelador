from typing import List, Tuple

import safe_socket
from lottery.bet import Bet

# Protocol Operation Types
OP_BATCH = 0x01
OP_BATCH_ACK = 0x02
OP_END = 0x03
OP_WINNERS = 0x04
# Protocol Parameter Sizes
HEADER_SIZE = 5
OP_CODE_SIZE = 1
PAYLOAD_SIZE = 4
AGENCY_SIZE = 4
NAME_LEN_SIZE = 1
LAST_LEN_SIZE = 1
USER_ID_SIZE = 4
BIRTH_DATE_SIZE = 10
CODE_SIZE = 4


def send_message(socket, opcode: int, payload: bytes):
    header = bytearray(HEADER_SIZE)
    header[0] = opcode
    header[OP_CODE_SIZE:] = len(payload).to_bytes(PAYLOAD_SIZE, byteorder="big")

    msg = header + payload
    safe_socket.send_all(socket, msg)


def recv_message(socket) -> Tuple[int, bytes]:
    header = safe_socket.recv_all(socket, HEADER_SIZE)
    if not header:
        return 0, b""

    opcode = header[0]
    length = int.from_bytes(header[OP_CODE_SIZE:HEADER_SIZE], byteorder="big")

    payload = b""
    if length > 0:
        payload = safe_socket.recv_all(socket, length)

    return opcode, payload


def serialize_bet(bet: Bet) -> bytes:
    name_bytes = bet.first_name.encode("utf-8")
    last_bytes = bet.last_name.encode("utf-8")
    birth_bytes = bet.birthdate.encode("utf-8")  # 10 bytes

    data = bytearray()
    data.extend(bet.agency_id.to_bytes(AGENCY_SIZE, byteorder="big"))
    data.append(len(name_bytes))
    data.extend(name_bytes)
    data.append(len(last_bytes))
    data.extend(last_bytes)
    data.extend(bet.document.to_bytes(USER_ID_SIZE, byteorder="big"))
    data.extend(birth_bytes)
    data.extend(bet.number.to_bytes(CODE_SIZE, byteorder="big"))

    return bytes(data)


def deserialize_bet(data: bytes, offset: int) -> Tuple[Bet, int]:
    # Returns bet and new offset
    agency_id = int.from_bytes(data[offset : offset + AGENCY_SIZE], byteorder="big")
    offset += AGENCY_SIZE

    name_len = data[offset]
    offset += NAME_LEN_SIZE
    first_name = data[offset : offset + name_len].decode("utf-8")
    offset += name_len

    last_len = data[offset]
    offset += LAST_LEN_SIZE
    last_name = data[offset : offset + last_len].decode("utf-8")
    offset += last_len

    document = int.from_bytes(data[offset : offset + USER_ID_SIZE], byteorder="big")
    offset += USER_ID_SIZE

    birthdate = data[offset : offset + BIRTH_DATE_SIZE].decode("utf-8")
    offset += BIRTH_DATE_SIZE

    number = int.from_bytes(data[offset : offset + CODE_SIZE], byteorder="big")
    offset += CODE_SIZE

    bet = Bet(
        agency_id=agency_id,
        first_name=first_name,
        last_name=last_name,
        document=document,
        birthdate=birthdate,
        number=number,
    )

    return bet, offset


def deserialize_batch(payload: bytes) -> List[Bet]:
    bets = []
    offset = 0
    while offset < len(payload):
        bet, offset = deserialize_bet(payload, offset)
        bets.append(bet)
    return bets


def serialize_winners(winners: List[Bet]) -> bytes:
    winners_payload = bytearray()
    for winner in winners:
        winners_payload.extend(serialize_bet(winner))
    return bytes(winners_payload)
