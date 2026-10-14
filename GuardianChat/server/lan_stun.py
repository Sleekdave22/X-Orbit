"""LAN-only STUN Binding service. Address discovery only; never relays media."""
import ipaddress,socket,struct,threading,time,zlib
COOKIE=0x2112A442

def response(data,address):
 if len(data)<20 or len(data)>576:return None
 kind,length,cookie=struct.unpack('!HHI',data[:8])
 if kind!=1 or cookie!=COOKIE or length%4 or len(data)!=20+length:return None
 ip=ipaddress.ip_address(address[0])
 if ip.version!=4 or not ip.is_private:return None
 mapped=struct.pack('!BBHI',0,1,address[1]^(COOKIE>>16),int(ip)^COOKIE)
 body=struct.pack('!HH',0x0020,8)+mapped
 packet=struct.pack('!HHI',0x0101,len(body)+8,COOKIE)+data[8:20]+body
 return packet+struct.pack('!HHI',0x8028,4,zlib.crc32(packet)^0x5354554e)

def start(port=3478):
 sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
 try:sock.bind(('0.0.0.0',port))
 except OSError:sock.close();print('LAN address discovery unavailable on UDP '+str(port),flush=True);return None
 def serve():
  windows={}
  while True:
   try:
    data,addr=sock.recvfrom(577);now=int(time.monotonic());last,count=windows.get(addr[0],(now,0));count=count+1 if last==now else 1;windows[addr[0]]=(now,count)
    if len(windows)>256:windows.clear()
    if count>40:continue
    reply=response(data,addr)
    if reply:sock.sendto(reply,addr)
   except (OSError,ValueError):continue
 threading.Thread(target=serve,daemon=True,name='lan-address-discovery').start();return sock
