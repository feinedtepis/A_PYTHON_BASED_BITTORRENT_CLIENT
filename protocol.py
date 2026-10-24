
import struct

PROTOCOL = b"BitTorrent protocol"

CHOKE = 0
UNCHOKE = 1
INTERESTED = 2
NOT_INTERESTED = 3
HAVE = 4
BITFIELD = 5
REQUEST = 6
PIECE = 7


def handshake(info_hash, peer_id):
    if isinstance(info_hash, str):
        info_hash = bytes.fromhex(info_hash)

    if isinstance(peer_id, str):
        peer_id = peer_id.encode()

    if len(info_hash) != 20 or len(peer_id) != 20:
        raise ValueError("Info hash and peer ID must be 20 bytes")

    return (
        bytes([len(PROTOCOL)])
        + PROTOCOL
        + bytes(8)
        + info_hash
        + peer_id
    )


def message(message_id, payload=b""):
    length = 1 + len(payload)
    return struct.pack(">IB", length, message_id) + payload


def interested():
    return message(INTERESTED)


def request(piece_index, offset, length):
    payload = struct.pack(">III", piece_index, offset, length)
    return message(REQUEST, payload)


def decode_bitfield(data, piece_count):
    result = []

    for byte in data:
        for bit in range(7, -1, -1):
            result.append(bool(byte & (1 << bit)))

    return result[:piece_count]


def decode_piece(payload):
    if len(payload) < 8:
        raise ValueError("Invalid piece message")

    piece_index, offset = struct.unpack(">II", payload[:8])
    block = payload[8:]

    return piece_index, offset, block


async def read_message(reader):
    length_bytes = await reader.readexactly(4)
    length = struct.unpack(">I", length_bytes)[0]

    if length == 0:
        return None, b""  # Keep-alive

    if length > 1024 * 1024:
        raise ValueError("Message too large")

    data = await reader.readexactly(length)

    return data[0], data[1:]


async def read_handshake(reader, expected_info_hash):
    response = await reader.readexactly(68)

    if response[0] != 19 or response[1:20] != PROTOCOL:
        raise ValueError("Invalid BitTorrent handshake")

    if isinstance(expected_info_hash, str):
        expected_info_hash = bytes.fromhex(expected_info_hash)

    if response[28:48] != expected_info_hash:
        raise ValueError("Peer belongs to another torrent")

    return response[48:68]
