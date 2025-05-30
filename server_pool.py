import socket
import threading
from concurrent.futures import ThreadPoolExecutor
import logging
from file_protocol import FileProtocol

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ThreadPoolServer:
    def __init__(self, ipaddress='0.0.0.0', port=6666, pool_size=5):
        self.ipinfo = (ipaddress, port)
        self.pool_size = pool_size
        self.pool = ThreadPoolExecutor(max_workers=pool_size)
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.fp = FileProtocol()

    def handle_client(self, connection, address):
        try:
            logging.info(f"Thread {threading.current_thread().name} handling client {address}")
            
            # Increased buffer for large files
            data = connection.recv(8192)
            if not data:
                return
            
            d = data.decode('utf-8')
            hasil = self.fp.proses_string(d)
            hasil = hasil + "\r\n\r\n"
            connection.sendall(hasil.encode('utf-8'))
                
        except Exception as e:
            logging.error(f"Error handling client {address}: {e}")
        finally:
            connection.close()
            logging.info(f"Connection with {address} closed")

    def run(self):
        try:
            self.my_socket.bind(self.ipinfo)
            self.my_socket.listen(10)
            logging.info(f"ThreadPool Server running on {self.ipinfo} with {self.pool_size} workers")

            while True:
                connection, address = self.my_socket.accept()
                logging.info(f"New connection from {address}")
                self.pool.submit(self.handle_client, connection, address)
                
        except KeyboardInterrupt:
            logging.info("Server shutdown requested")
        except Exception as e:
            logging.error(f"Server error: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        self.pool.shutdown(wait=True)
        self.my_socket.close()
        logging.info("Server cleaned up")

if __name__ == "__main__":
    server = ThreadPoolServer(pool_size=5)
    server.run()