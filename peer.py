
import asyncio
import secrets

from protocol import (
    handshake,
    read_handshake,
    read_message,
    decode_bitfield,
    decode_piece,
    interested,
    request,
    BITFIELD,
    HAVE,
    CHOKE,
    UNCHOKE,
    PIECE
)

MAX_PEERS = 5

CONNECT_TIMEOUT = 5
HANDSHAKE_TIMEOUT = 5
PEER_READY_TIMEOUT = 30
BLOCK_TRANSFER_TIMEOUT = 20

BLOCK_SIZE = 16 * 1024


async def connect_peer(
    ip, port, info_hash, piece_count, piece_length, total_size
):
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(ip, port),
        timeout=CONNECT_TIMEOUT
    )

    peer_id = "-PY0001-" + secrets.token_hex(6)

    try:
        # Step 1: Handshake
        writer.write(handshake(info_hash, peer_id))
        await writer.drain()

        remote_id = await asyncio.wait_for(
            read_handshake(reader, info_hash),
            timeout=HANDSHAKE_TIMEOUT
        )

        print(f"Handshake successful: {ip}:{port}")

        available = [False] * piece_count
        unchoked = False
        requested = False
        piece_index = None

        next_offset = 0
        expected_length = 0
        blocks = {}

        # Step 2: Tell peer we're interested
        writer.write(interested())
        await writer.drain()

        print(f"Interested sent: {ip}:{port}")

        # Step 3: Wait for a peer that can supply data
        async with asyncio.timeout(PEER_READY_TIMEOUT):
            while not (unchoked and any(available)):
                msg_id, payload = await read_message(reader)

                if msg_id == BITFIELD:
                    decoded = decode_bitfield(payload, piece_count)
                    available = [
                        old or new
                        for old, new in zip(available, decoded)
                    ]

                elif msg_id == HAVE:
                    if len(payload) != 4:
                        raise ValueError("Invalid HAVE message")

                    index = int.from_bytes(payload, "big")
                    if 0 <= index < piece_count:
                        available[index] = True

                elif msg_id == UNCHOKE:
                    unchoked = True

                elif msg_id == CHOKE:
                    unchoked = False

        # Step 4: Select a piece
        piece_index = available.index(True)

        piece_start = piece_index * piece_length
        actual_piece_length = min(
            piece_length,
            total_size - piece_start
        )

        if actual_piece_length <= 0:
            raise ValueError("Invalid piece length")

        print(
            f"Downloading piece {piece_index} "
            f"({actual_piece_length} bytes)"
        )

        # Step 5: Download all blocks of this piece
        while next_offset < actual_piece_length:

            if unchoked and not requested:
                expected_length = min(
                    BLOCK_SIZE,
                    actual_piece_length - next_offset
                )

                writer.write(
                    request(
                        piece_index,
                        next_offset,
                        expected_length
                    )
                )
                await writer.drain()

                requested = True

                print(
                    f"Requested piece={piece_index}, "
                    f"offset={next_offset}, "
                    f"length={expected_length}"
                )

            # Each block has its own timeout.
            async with asyncio.timeout(BLOCK_TRANSFER_TIMEOUT):
                while requested:
                    msg_id, payload = await read_message(reader)

                    if msg_id == PIECE:
                        index, offset, block = decode_piece(payload)

                        if (
                            index != piece_index
                            or offset != next_offset
                            or len(block) != expected_length
                        ):
                            raise ValueError(
                                "Unexpected PIECE response"
                            )

                        blocks[offset] = block

                        next_offset += len(block)
                        requested = False

                        print(
                            f"Received {len(block)} bytes | "
                            f"Progress: {next_offset}/{actual_piece_length}"
                        )

                    elif msg_id == CHOKE:
                        raise ConnectionError(
                            "Peer choked during transfer"
                        )

                    elif msg_id == HAVE:
                        if len(payload) != 4:
                            raise ValueError("Invalid HAVE message")

                        index = int.from_bytes(payload, "big")
                        if 0 <= index < piece_count:
                            available[index] = True

                    elif msg_id == UNCHOKE:
                        unchoked = True

                    # Ignore other messages, including keep-alives.

        # Step 6: Assemble the complete piece
        piece_data = b"".join(
            blocks[offset] for offset in sorted(blocks)
        )

        if len(piece_data) != actual_piece_length:
            raise ValueError("Incomplete piece")

        print(
            f"Complete piece {piece_index} received: "
            f"{len(piece_data)} bytes"
        )

        return {
            "address": (ip, port),
            "piece_index": piece_index,
            "piece_data": piece_data
        }

    finally:
        writer.close()
        await writer.wait_closed()


async def peer_worker(
    address, info_hash, piece_count, piece_length, total_size
):
    ip, port = address

    try:
        return await connect_peer(
            ip,
            port,
            info_hash,
            piece_count,
            piece_length,
            total_size
        )

    except (
        OSError,
        TimeoutError,
        ValueError,
        asyncio.IncompleteReadError
    ) as e:
        print(f"Peer failed: {ip}:{port} -> {e}")
        return None


async def manage_peers(
    peers, info_hash, piece_count, piece_length, total_size
):
    attempted_peers = set()
    received_pieces = []

    semaphore = asyncio.Semaphore(MAX_PEERS)

    async def run_worker(address):
        async with semaphore:
            result = await peer_worker(
                address,
                info_hash,
                piece_count,
                piece_length,
                total_size
            )

            if result is not None:
                received_pieces.append(result)

    tasks = []

    for address in peers:
        if address in attempted_peers:
            continue

        attempted_peers.add(address)
        tasks.append(asyncio.create_task(run_worker(address)))

    await asyncio.gather(*tasks)

    return received_pieces
