
import asyncio

from metadata import get_metadata
from tracker import get_peers_from_tracker
from peer import manage_peers


async def main():
    # Step 1: Load torrent metadata
    metadata = get_metadata("hail_mary.torrent")

    print("Torrent:", metadata["name"])

    piece_count = len(metadata["piece_hashes"])

    print("Total size:", metadata["total_size"])
    print("Piece length:", metadata["piece_length"])
    print("Total pieces:", piece_count)

    # Step 2: Discover peers
    peers = get_peers_from_tracker(
        metadata["torrent"],
        metadata["trackers"]
    )

    print("\nDiscovered peers:", len(peers))

    if not peers:
        print("No peers discovered.")
        return

    # Step 3: Connect and download one block per successful peer
    received_blocks = await manage_peers(
        peers,
        metadata["info_hash"],
        piece_count
    )

    # Step 4: Display received blocks
    print("\nBlocks received:", len(received_blocks))

    total_bytes = 0

    for result in received_blocks:
        address = result["address"]
        piece_index = result["piece_index"]
        offset = result["offset"]
        block = result["block"]

        total_bytes += len(block)

        print(
            f"Peer: {address} | "
            f"Piece: {piece_index} | "
            f"Offset: {offset} | "
            f"Bytes: {len(block)}"
        )

    print("\nTotal bytes received:", total_bytes)

    if received_blocks:
        print("Successfully received torrent data!")
    else:
        print("No blocks received from the discovered peers.")


if __name__ == "__main__":
    asyncio.run(main())
