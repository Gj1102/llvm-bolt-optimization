import socket, socketserver, select
class Relay(socketserver.BaseRequestHandler):
    def handle(self):
        with socket.create_connection(('127.0.0.1',7897),timeout=20) as upstream:
            peers=[self.request, upstream]
            while True:
                ready,_,_=select.select(peers,[],[],120)
                if not ready: return
                for source in ready:
                    data=source.recv(65536)
                    if not data: return
                    (upstream if source is self.request else self.request).sendall(data)
class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address=True
Server(('172.26.208.1',18797),Relay).serve_forever()
