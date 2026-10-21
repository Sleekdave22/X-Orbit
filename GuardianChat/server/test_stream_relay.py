"""Actual ICE / DTLS / RTP tests, with synthetic media and an isolated database."""
import asyncio
from fractions import Fraction
import time
import unittest
import urllib.error

import match_streams
import stream_lifecycle as life
import stream_relay
import test_match_streams as fixtures
import test_server

if stream_relay.AVAILABLE:
    from aiortc import RTCPeerConnection, RTCConfiguration, RTCSessionDescription, VideoStreamTrack, MediaStreamTrack
    from av import VideoFrame, AudioFrame

    class TestVideo(VideoStreamTrack):
        def __init__(self):
            super().__init__(); self.pts = 0
        async def recv(self):
            await asyncio.sleep(.1)
            frame = VideoFrame(width=160, height=96, format='yuv420p')
            for plane in frame.planes:
                plane.update(bytes([100]) * plane.buffer_size)
            frame.pts = self.pts; self.pts += 9000; frame.time_base = Fraction(1, 90000)
            return frame

    class TestAudio(MediaStreamTrack):
        kind = 'audio'
        def __init__(self):
            super().__init__(); self.pts = 0
        async def recv(self):
            await asyncio.sleep(.02)
            frame = AudioFrame(format='s16', layout='mono', samples=960)
            for plane in frame.planes: plane.update(bytes(plane.buffer_size))
            frame.sample_rate = 48000; frame.pts = self.pts
            self.pts += 960; frame.time_base = Fraction(1, 48000)
            return frame


@unittest.skipUnless(stream_relay.AVAILABLE, 'Install requirements-streaming.txt to test actual RTP')
class RelayMediaTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.fixture = fixtures.MatchStreamsTest(); self.fixture.setUp(); self.server = self.fixture.s
        self.server.stream_relay = stream_relay.StreamRelay(self.server)
        self.relay = self.server.stream_relay
        self.peers = []
        self.audio_received = 0
        self.room = match_streams.create(self.server, 'u0', {'kind': 'open', 'match': 'match'})['id']
        with self.server.db() as d: life.begin(d, 'u0', self.room)

    async def asyncTearDown(self):
        await asyncio.gather(*(pc.close() for pc in self.peers), return_exceptions=True)
        await asyncio.to_thread(self.relay.close)
        self.fixture.tearDown()

    async def connect(self, uid, role, frames=None):
        pc = RTCPeerConnection(RTCConfiguration(iceServers=[])); self.peers.append(pc)
        if role == 'publish':
            pc.addTrack(TestVideo()); pc.addTrack(TestAudio())
        else:
            pc.addTransceiver('video', direction='recvonly')
            pc.addTransceiver('audio', direction='recvonly')
            @pc.on('track')
            async def received(track):
                frame = await track.recv()
                if track.kind == 'audio': self.audio_received += 1
                elif not frames.done(): frames.set_result(frame)
        await pc.setLocalDescription(await pc.createOffer())
        body = dict(room=self.room, role=role, type='offer', sdp=pc.localDescription.sdp, client_id=uid)
        answer = await asyncio.to_thread(self.relay.offer, uid, body)
        await pc.setRemoteDescription(RTCSessionDescription(sdp=answer['sdp'], type=answer['type']))
        return answer, body

    async def until(self, check, seconds=12):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if check(): return
            await asyncio.sleep(.1)
        self.fail('Media state did not settle before timeout')

    async def test_single_publisher_six_decoding_viewers_permissions_and_teardown(self):
        self.assertFalse(self.relay.ready(self.room))
        publisher, body = await self.connect('u0', 'publish')
        await self.until(lambda: self.relay.ready(self.room))
        self.assertEqual(await asyncio.to_thread(self.relay.offer, 'u0', body), publisher)
        self.assertEqual(len(match_streams.list_streams(self.server, 'u2')['streams']), 1)
        pending = []
        answers = []
        for n in range(2, 8):
            uid = 'u' + str(n); match_streams.join(self.server, uid, self.room)
            future = asyncio.get_running_loop().create_future(); pending.append(future)
            answer, _ = await self.connect(uid, 'watch', future); answers.append(answer)
        frames = await asyncio.wait_for(asyncio.gather(*pending), 20)
        self.assertTrue(all(f.width == 160 and f.height == 96 for f in frames))
        await self.until(lambda: self.audio_received == 6)
        # Six actual receiving RTP peers still use one source connection.
        self.assertEqual(sum(p['role'] == 'publish' for p in self.relay._peers.values()), 1)
        self.assertEqual(len(self.relay._rooms), 1)
        with self.assertRaises(PermissionError):
            await asyncio.to_thread(self.relay.close_peer, 'u9', dict(room=self.room, peer_id=answers[0]['peer_id']))
        for n in range(2, 8):
            with self.server.db() as d: life.watch(d, 'u' + str(n), self.room)
        with self.server.db() as d: d.execute('INSERT INTO social_blocks VALUES(?,?)', ('u0', 'u2'))
        await self.until(lambda: answers[0]['peer_id'] not in self.relay._peers)
        self.assertTrue(self.relay.ready(self.room))
        await asyncio.to_thread(self.relay.close_peer, 'u0', dict(room=self.room, peer_id=publisher['peer_id']))
        self.assertFalse(self.relay.ready(self.room))
        self.assertEqual(self.relay._peers, {})
        self.assertEqual(match_streams.list_streams(self.server, 'u8')['streams'], [])
        with self.server.db() as d:
            self.assertEqual(life.total(d, 'u0'), 6)
            self.assertEqual(d.execute('SELECT COUNT(*) FROM game_stream_rooms').fetchone()[0], 0)

    async def test_invalid_offer_and_unjoined_viewer_create_no_connections(self):
        with self.assertRaises(ValueError):
            self.relay.offer('u0', dict(room=self.room, role='publish', type='answer', sdp='x' * 20, client_id='a'))
        with self.assertRaises(PermissionError):
            self.relay.offer('u2', dict(room=self.room, role='watch', type='offer', sdp='x' * 20, client_id='a'))
        self.assertEqual(self.relay._peers, {})


@unittest.skipUnless(stream_relay.AVAILABLE, 'Install requirements-streaming.txt')
class RelayHTTPTest(unittest.TestCase):
    setUp = test_server.ChatTest.setUp
    tearDown = test_server.ChatTest.tearDown
    call = test_server.ChatTest.call
    register = test_server.ChatTest.register

    def test_authenticated_routes_creation_join_and_offer_validation(self):
        a, b, viewer = [self.register(name) for name in ('Host', 'Opponent', 'Viewer')]
        self.call('/gaming/profile', dict(tag='Host', game_id='host-game', adult=True), a['token'])
        with self.server.db() as d:
            now = int(time.time())
            d.execute("INSERT INTO gb_matches(id,game,a,b,state,created,deadline,rules) VALUES('http-match','efootball',?,?,'in_progress',?,?,'{}')", (a['id'], b['id'], now, now + 3600))
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.call('/gaming/live-streams')
        self.assertEqual(error.exception.code, 401)
        room = self.call('/gaming/match_stream_create', dict(kind='open', match='http-match'), a['token'])
        self.assertEqual(room['media'], 'relay')
        self.assertEqual(self.call('/gaming/live-streams', token=viewer['token']), {'streams': []})
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.call('/gaming/match_stream_create', dict(kind='open', match='http-match'), viewer['token'])
        self.assertEqual(error.exception.code, 403)
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.call('/gaming/stream_join', dict(room=room['id']), viewer['token'])
        self.assertEqual(error.exception.code, 403)
        self.call('/gaming/stream_begin', dict(room=room['id']), a['token'])
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.call('/gaming/stream_relay_offer', dict(room=room['id'], role='publish', type='answer', sdp='invalid', client_id='http'), a['token'])
        self.assertEqual(error.exception.code, 400)
        self.assertEqual(self.call('/gaming/stream_relay_close', dict(room=room['id'], peer_id='none'), a['token']), {'closed': True})
        self.call('/gaming/stream_end', dict(room=room['id']), a['token'])


if __name__ == '__main__': unittest.main()
