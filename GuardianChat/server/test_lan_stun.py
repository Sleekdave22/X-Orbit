import unittest,struct,ipaddress,zlib
import lan_stun
class LANStunTest(unittest.TestCase):
 def test_binding_maps_only_private_address(self):
  tid=b'123456789012';packet=struct.pack('!HHI',1,0,lan_stun.COOKIE)+tid
  reply=lan_stun.response(packet,('192.168.1.22',45678));self.assertEqual(reply[8:20],tid)
  self.assertEqual(struct.unpack('!H',reply[26:28])[0]^(lan_stun.COOKIE>>16),45678)
  self.assertEqual(struct.unpack('!I',reply[28:32])[0]^lan_stun.COOKIE,int(ipaddress.ip_address('192.168.1.22')))
  self.assertEqual(struct.unpack('!I',reply[-4:])[0],zlib.crc32(reply[:-8])^0x5354554e)
  self.assertIsNone(lan_stun.response(packet,('8.8.8.8',45678)));self.assertIsNone(lan_stun.response(b'photo',('192.168.1.22',45678)))
