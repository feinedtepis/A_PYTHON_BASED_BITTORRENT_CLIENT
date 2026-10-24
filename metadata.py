
from torrentlib import Torrent, TorrentMetaInfo


def get_metadata(path="hail_mary.torrent"):
    torrent = Torrent.from_file(path)
    meta = TorrentMetaInfo.from_file(path)

    info = meta.data[b"info"]

    piece_length = info[b"piece length"]
    raw_hashes = info[b"pieces"]

    piece_hashes = [
        raw_hashes[i:i+20]
        for i in range(0, len(raw_hashes), 20)
    ]

    tracker = meta.data[b"announce"].decode("utf-8")
    trackers = meta.data.get(b"announce-list", [])

    trackersli = []

    if trackers:
        for tier in trackers:
            for tr in tier:
                trackersli.append(tr.decode("utf-8"))
    else:
        trackersli = [tracker]
    li= {
        "torrent": torrent,
        "name": torrent.name,
        "info_hash": torrent.info_hash,
        "total_size": torrent.total_size,
        "piece_length": piece_length,
        "piece_hashes": piece_hashes,
        "trackers": trackersli  
    }
    print(li)
    return {
        "torrent": torrent,
        "name": torrent.name,
        "info_hash": torrent.info_hash,
        "total_size": torrent.total_size,
        "piece_length": piece_length,
        "piece_hashes": piece_hashes,
        "trackers": trackersli
    }
get_metadata()