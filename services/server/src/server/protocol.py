import struct
from typing import Tuple
import safe_socket

OP_BATCH = 0x01
OP_BATCH_ACK = 0x02
OP_END = 0x03
OP_WINNERS = 0x04

def send_message(socket, opcode: int, payload: bytes):
    header = bytearray(5)
    header[0] = opcode
    header[1:] = len(payload).to_bytes(4, byteorder='big')
    
    safe_socket.send_all(socket, header)
    if payload:
        safe_socket.send_all(socket, payload)

def recv_message(socket) -> Tuple[int, bytes]:
    header = safe_socket.recv_all(socket, 5)
    if not header:
        return 0, b''
    
    opcode = header[0]
    length = int.from_bytes(header[1:5], byteorder='big')
    
    payload = b''
    if length > 0:
        payload = safe_socket.recv_all(socket, length)
        
    return opcode, payload

def serialize_bet(bet) -> bytes:
    name_bytes = bet.first_name.encode('utf-8')
    last_bytes = bet.last_name.encode('utf-8')
    birth_bytes = bet.birthdate.encode('utf-8') # 10 bytes
    
    data = bytearray()
    data.extend(bet.agency_id.to_bytes(4, byteorder='big'))
    data.append(len(name_bytes))
    data.extend(name_bytes)
    data.append(len(last_bytes))
    data.extend(last_bytes)
    data.extend(bet.document.to_bytes(4, byteorder='big'))
    data.extend(birth_bytes)
    data.extend(bet.number.to_bytes(4, byteorder='big'))
    
    return bytes(data)

def deserialize_bet(data: bytes, offset: int):
    # Returns bet and new offset
    from lottery.bet import Bet
    
    agency_id = int.from_bytes(data[offset:offset+4], byteorder='big')
    offset += 4
    
    name_len = data[offset]
    offset += 1
    first_name = data[offset:offset+name_len].decode('utf-8')
    offset += name_len
    
    last_len = data[offset]
    offset += 1
    last_name = data[offset:offset+last_len].decode('utf-8')
    offset += last_len
    
    document = int.from_bytes(data[offset:offset+4], byteorder='big')
    offset += 4
    
    birthdate = data[offset:offset+10].decode('utf-8')
    offset += 10
    
    number = int.from_bytes(data[offset:offset+4], byteorder='big')
    offset += 4
    
    bet = Bet(
        agency_id=agency_id,
        first_name=first_name,
        last_name=last_name,
        document=document,
        birthdate=birthdate,
        number=number
    )
    
    return bet, offset
