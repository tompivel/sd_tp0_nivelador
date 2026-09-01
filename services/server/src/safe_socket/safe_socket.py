import socket


def recv_all(sock: socket.socket, size: int) -> bytes:
    chunks = []
    bytes_recd = 0
    while bytes_recd < size:
        chunk = sock.recv(size - bytes_recd)
        if chunk == b"":
            raise ConnectionError("socket connection broken")
        chunks.append(chunk)
        bytes_recd += len(chunk)
    return b"".join(chunks)


def send_all(sock: socket.socket, data: bytes):
    total_sent = 0
    while total_sent < len(data):
        sent = sock.send(data[total_sent:])
        total_sent += sent
