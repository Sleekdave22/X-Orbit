"""In-memory LAN WebRTC relay. One publisher upload, server fan-out to viewers.

No recording and no fixed spectator cap. CPU / bandwidth still bound capacity;
this decode/encode relay is not a distributed SFU. Importing it is optional so
ordinary chat and existing installations can start without media dependencies.
"""
import asyncio
import hashlib
import threading
import time
import uuid

try:
    from aiortc import RTCPeerConnection, RTCConfiguration, RTCSessionDescription, MediaStreamTrack
    from aiortc.contrib.media import MediaBlackhole, MediaRelay
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


class RelayUnavailable(ValueError):
    pass


if AVAILABLE:
    class ObservedTrack(MediaStreamTrack):
        def __init__(self, track, received):
            super().__init__()
            self.kind = track.kind
            self.source = track
            self.received = received

        async def recv(self):
            frame = await self.source.recv()
            self.received(self.kind)
            return frame

        def stop(self):
            super().stop()
            self.source.stop()


class StreamRelay:
    def __init__(self, server):
        self.server = server
        self.enabled = AVAILABLE
        self._lock = threading.RLock()
        self._ready = {}
        self._loop = None
        self._thread = None
        self._closed = False
        # These collections belong exclusively to the media event loop.
        self._rooms = {}
        self._peers = {}

    def ready(self, room):
        with self._lock:
            status = self._ready.get(room)
            return bool(status and status[0] and time.monotonic() - status[1] < 12)

    def _start(self):
        with self._lock:
            if self._closed:
                raise RelayUnavailable('Live broadcasting is shutting down')
            if not self.enabled:
                raise RelayUnavailable('The server media relay is not installed')
            if self._loop is None:
                self._loop = asyncio.new_event_loop()
                def run():
                    asyncio.set_event_loop(self._loop)
                    self._loop.create_task(self._health())
                    self._loop.run_forever()
                    pending = asyncio.all_tasks(self._loop)
                    for task in pending:
                        task.cancel()
                    self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                    self._loop.close()
                self._thread = threading.Thread(target=run, name='OrbitMediaRelay', daemon=True)
                self._thread.start()

    def offer(self, uid, body, session_hash=None):
        room = str(body.get('room', ''))
        role = body.get('role')
        sdp = body.get('sdp')
        client = str(body.get('client_id', ''))
        if (role not in ('publish', 'watch') or body.get('type') != 'offer'
                or not isinstance(sdp, str) or not 10 < len(sdp) < 100000
                or not client or len(client) > 100 or len(room) != 32):
            raise ValueError('Invalid livestream connection request')
        import match_streams
        match_streams.authorize(self.server, uid, room, publish=role == 'publish')
        with self.server.db() as d:
            __import__('stream_lifecycle').active(d, room)
        self._start()
        future = asyncio.run_coroutine_threadsafe(self._offer(uid, room, role, client, sdp, session_hash), self._loop)
        try:
            return future.result(timeout=25)
        except TimeoutError:
            future.cancel()
            raise ValueError('Live connection timed out; please reconnect') from None

    def close_peer(self, uid, body):
        pid = str(body.get('peer_id', '')); room = str(body.get('room', ''))
        if not pid or not self._loop:
            return {'closed': True}
        return asyncio.run_coroutine_threadsafe(self._close_owned(uid, room, pid), self._loop).result(timeout=15)

    async def _close_owned(self, uid, room, pid):
        peer = self._peers.get(pid)
        if peer:
            if peer['uid'] != uid or peer['room'] != room:
                raise PermissionError('This live connection belongs to another account')
            await self._drop(pid)
        return {'closed': True}

    async def _offer(self, uid, room, role, client, sdp, session_hash):
        import match_streams
        digest = hashlib.sha256(sdp.encode()).hexdigest()
        for old in self._peers.values():
            if (old['uid'], old['room'], old['role']) == (uid, room, role):
                if old['client'] == client and old['digest'] == digest and old.get('answer'):
                    return old['answer']
                if role == 'publish':
                    raise ValueError('This room is already broadcasting; stop it before restarting')
                await self._drop(old['id'])
                break
        if role == 'publish' and room in self._rooms:
            raise ValueError('This live room already has a broadcaster')
        if role == 'watch' and not self.ready(room):
            raise PermissionError('This livestream is not broadcasting right now')
        pc = RTCPeerConnection(RTCConfiguration(iceServers=[]))
        pid = uuid.uuid4().hex
        entry = dict(id=pid, pc=pc, uid=uid, room=room, role=role, client=client, digest=digest,
                     created=time.monotonic(), proxies=[], session_hash=session_hash)
        self._peers[pid] = entry
        broadcast = None
        if role == 'publish':
            broadcast = dict(peer=pid, tracks={}, relay=MediaRelay(), sink=MediaBlackhole(), frame=0.0)
            self._rooms[room] = broadcast
            with self._lock:
                self._ready[room] = (False, 0)

        @pc.on('track')
        def on_track(track):
            if role != 'publish' or self._rooms.get(room) is not broadcast:
                track.stop()
                return
            if track.kind not in ('audio', 'video') or track.kind in broadcast['tracks']:
                track.stop()
                return
            def received(kind):
                if kind == 'video' and self._rooms.get(room) is broadcast:
                    broadcast['frame'] = time.monotonic()
                    with self._lock:
                        self._ready[room] = (pc.connectionState == 'connected', broadcast['frame'])
            observed = ObservedTrack(track, received)
            broadcast['tracks'][track.kind] = observed
            broadcast['sink'].addTrack(broadcast['relay'].subscribe(observed, buffered=False))

            @track.on('ended')
            async def on_ended():
                if track.kind == 'video' and self._rooms.get(room) is broadcast:
                    await self._end(room, finalize=True)

        @pc.on('connectionstatechange')
        async def state_changed():
            if self._peers.get(pid) is not entry:
                return
            if role == 'publish':
                with self._lock:
                    self._ready[room] = (pc.connectionState == 'connected', broadcast['frame'])
            if pc.connectionState in ('failed', 'closed'):
                await self._drop(pid)
            elif pc.connectionState == 'disconnected':
                await asyncio.sleep(10)
                if pc.connectionState == 'disconnected' and self._peers.get(pid) is entry:
                    await self._drop(pid)

        try:
            await pc.setRemoteDescription(RTCSessionDescription(sdp=sdp, type='offer'))
            if role == 'publish':
                if 'video' not in broadcast['tracks']:
                    raise ValueError('A live broadcast needs a video track')
                await broadcast['sink'].start()
            else:
                source = self._rooms[room]
                for transceiver in pc.getTransceivers():
                    track = source['tracks'].get(transceiver.kind)
                    if track and transceiver.direction in ('recvonly', 'sendrecv'):
                        proxy = source['relay'].subscribe(track, buffered=False)
                        entry['proxies'].append(proxy)
                        pc.addTrack(proxy)
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)
            # Permissions and match eligibility may have changed during negotiation.
            match_streams.authorize(self.server, uid, room, publish=role == 'publish')
            with self.server.db() as d:
                __import__('stream_lifecycle').active(d, room)
            if self._peers.get(pid) is not entry:
                raise ValueError('This livestream connection has ended')
            entry['answer'] = {'type': pc.localDescription.type, 'sdp': pc.localDescription.sdp, 'peer_id': pid}
            return entry['answer']
        except BaseException:
            await self._drop(pid)
            raise

    async def _drop(self, pid):
        peer = self._peers.get(pid)
        if not peer:
            return
        if peer['role'] == 'publish':
            await self._end(peer['room'], finalize=True)
        else:
            self._peers.pop(pid, None)
            # Keep the unique-session history, but expire the current-viewer lease.
            with self.server.db() as d:
                d.execute('UPDATE live_viewers SET heartbeat=0 WHERE room=? AND uid=?', (peer['room'], peer['uid']))
            for track in peer['proxies']:
                track.stop()
            await peer['pc'].close()

    def end_room(self, room):
        """Nonblocking: safe to call from an existing SQLite transaction."""
        with self._lock:
            self._ready.pop(room, None)
            loop = self._loop
        if loop and not self._closed:
            asyncio.run_coroutine_threadsafe(self._end(room, finalize=False), loop)

    async def _end(self, room, finalize):
        source = self._rooms.pop(room, None)
        with self._lock:
            self._ready.pop(room, None)
        peers = [p for p in list(self._peers.values()) if p['room'] == room]
        for peer in peers:
            self._peers.pop(peer['id'], None)
            for track in peer['proxies']:
                track.stop()
        if source:
            await source['sink'].stop()
            for track in source['tracks'].values():
                track.stop()
        await asyncio.gather(*(p['pc'].close() for p in peers), return_exceptions=True)
        if finalize and source:
            with self.server.db() as d:
                d.execute('BEGIN IMMEDIATE')
                __import__('stream_lifecycle').finish(d, room, self.server)

    async def _health(self):
        while True:
            await asyncio.sleep(5)
            import match_streams
            for pid, peer in list(self._peers.items()):
                try:
                    match_streams.authorize(self.server, peer['uid'], peer['room'], publish=peer['role'] == 'publish')
                    with self.server.db() as d:
                        __import__('stream_lifecycle').active(d, peer['room'])
                        if peer['session_hash'] and not d.execute('SELECT 1 FROM sessions WHERE token_hash=? AND user_id=?', (peer['session_hash'], peer['uid'])).fetchone():
                            raise PermissionError('Signed out')
                    if peer['pc'].connectionState != 'connected' and time.monotonic() - peer['created'] > 30:
                        raise PermissionError('Connection expired')
                    if peer['role'] == 'publish':
                        source = self._rooms.get(peer['room'])
                        if source and time.monotonic() - max(source['frame'], peer['created']) > 20:
                            raise PermissionError('Video feed stopped')
                except (PermissionError, ValueError):
                    await self._drop(pid)

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            loop = self._loop
        if loop:
            async def drain():
                for room in list(self._rooms):
                    await self._end(room, finalize=True)
            try:
                asyncio.run_coroutine_threadsafe(drain(), loop).result(timeout=15)
            finally:
                loop.call_soon_threadsafe(loop.stop)
                self._thread.join(timeout=5)
