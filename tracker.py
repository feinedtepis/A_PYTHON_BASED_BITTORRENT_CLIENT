
from torrentlib import TorrentStatus
from torrentlib.Tracker import Query
import secrets


def get_peers_from_tracker(torrent, trackers):
    torrent.event = TorrentStatus.STARTED

    peer_id = "-PY0001-" + secrets.token_hex(6)

    for tracker in trackers:
        try:
            print("Contacting:", tracker)

            response = Query.single(
                torrent=torrent,
                url=tracker,
                peer_id=peer_id,
                port=6881,
                timeout=10
            )

            print("Response:", response)

            peers = response.get("peers") or []
            peers6 = response.get("peers6") or []

            if peers or peers6:
                print("Peers found!")
                return peers + peers6

        except Exception as e:
            print("Tracker error:", e)

    return []
