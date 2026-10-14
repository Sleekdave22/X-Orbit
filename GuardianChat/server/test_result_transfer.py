"""Manual real-WebRTC photo test. Run directly; not a unit-test fixture."""
from pathlib import Path
import http.server,ssl,argparse
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8767);args=parser.parse_args();base=Path(__file__).resolve().parent
 class Handler(http.server.SimpleHTTPRequestHandler):
  def translate_path(self,path):
   if path=='/result-room.js':return str(base/'result-room.js')
   return str(base/'result-transfer-check'/('frame.html' if path.startswith('/frame.html') else 'index.html'))
 server=http.server.ThreadingHTTPServer(('0.0.0.0',args.port),Handler);ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(base/'tls/server.crt',base/'tls/server.key');server.socket=ctx.wrap_socket(server.socket,server_side=True);print('Run the main HTTPS server too for LAN address discovery. Test page uses synthetic data only.');server.serve_forever()
