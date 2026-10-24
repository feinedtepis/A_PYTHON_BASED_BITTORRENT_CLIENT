from torrentlib import Torrent, TorrentMetaInfo, TorrentStatus
from torrentlib.Tracker import Query
import os
import secrets
def get_metadata():
    torrent=Torrent.from_file("hail_mary.torrent")
    print(torrent.name)
    print(torrent.info_hash)
    print(torrent.total_size)
    meta=TorrentMetaInfo.from_file("hail_mary.torrent")
    tracker=meta.data[b"announce"].decode("utf-8")
    trackers=meta.data.get(b"announce-list", [])
    trackersli=[]
    
    if trackers:
        for t in trackers:
            for tr in t:
                print(tr.decode("utf-8"))
                trackersli.append(tr.decode("utf-8"))

    else:
        trackersli=[tracker]
    return trackersli #ik cheating but we do have a maint racker for this file

def get_peers_from_tracker():
    torrent=Torrent.from_file("libreoffice-help.torrent")
    trackers=get_metadata()
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

            if response.get("peers") or response.get("peers6"):
                print("Peers found!")
                break

        except Exception as e:
            print("Tracker error:", e)
        
    
if __name__ == "__main__":
    get_peers_from_tracker()
