from socket import *
import socket
import threading
import logging
import time
import sys
import os

from file_protocol import FileProtocol

# Setup logging yang lebih baik
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ProcessTheClient(threading.Thread):
    def __init__(self, connection, address):
        self.connection = connection
        self.address = address
        threading.Thread.__init__(self)

    def run(self):
        try:
            fp = FileProtocol()
            logging.info(f"Thread {self.name} handling client {self.address}")
            
            # Set socket options untuk performa yang lebih baik
            self.connection.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            self.connection.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
            self.connection.settimeout(120)  # 2 menit timeout
            
            # Receive data dengan handling yang lebih baik untuk file besar
            data_received = b""
            total_received = 0
            
            while True:
                try:
                    chunk = self.connection.recv(32768)  # 32KB chunks
                    if not chunk:
                        break
                    
                    data_received += chunk
                    total_received += len(chunk)
                    
                    # Log progress untuk file besar
                    if total_received % (1024 * 1024) == 0:  # Every 1MB
                        logging.info(f"Received {total_received // (1024*1024)}MB from {self.address}")
                    
                    # Check if we might have received complete command
                    # For small commands, break early
                    if len(chunk) < 32768 and not data_received.startswith(b'UPLOAD'):
                        break
                    
                    # For UPLOAD, we need to be more careful
                    if data_received.startswith(b'UPLOAD'):
                        # Look for the pattern: UPLOAD filename base64data
                        try:
                            decoded_so_far = data_received.decode('utf-8', errors='ignore')
                            parts = decoded_so_far.split(' ', 2)
                            if len(parts) >= 3:
                                # We have command, filename, and some data
                                # Check if base64 data looks complete (ends with proper padding)
                                base64_data = parts[2]
                                if len(base64_data) > 100 and (
                                    base64_data.endswith('=') or 
                                    base64_data.endswith('==') or
                                    len(chunk) < 32768  # Last chunk was smaller
                                ):
                                    break
                        except:
                            pass  # Keep receiving
                    
                except socket.timeout:
                    logging.warning(f"Timeout receiving from {self.address}, processing what we have")
                    break
                except Exception as e:
                    logging.error(f"Error receiving from {self.address}: {e}")
                    break
            
            if data_received:
                try:
                    # Decode received data
                    command_str = data_received.decode('utf-8')
                    logging.info(f"Processing {len(command_str)} characters from {self.address}")
                    
                    # Process command
                    result = fp.proses_string(command_str)
                    
                    # Send response
                    response = result + "\r\n\r\n"
                    response_bytes = response.encode('utf-8')
                    
                    # Send in chunks for large responses
                    chunk_size = 32768
                    total_sent = 0
                    
                    for i in range(0, len(response_bytes), chunk_size):
                        chunk = response_bytes[i:i + chunk_size]
                        self.connection.sendall(chunk)
                        total_sent += len(chunk)
                    
                    logging.info(f"Sent {total_sent} bytes response to {self.address}")
                    
                except UnicodeDecodeError as e:
                    logging.error(f"Unicode decode error from {self.address}: {e}")
                    error_response = '{"status": "ERROR", "message": "Invalid character encoding"}\r\n\r\n'
                    self.connection.sendall(error_response.encode('utf-8'))
                except Exception as e:
                    logging.error(f"Error processing request from {self.address}: {e}")
                    error_response = f'{{"status": "ERROR", "message": "Server processing error"}}\r\n\r\n'
                    self.connection.sendall(error_response.encode('utf-8'))
            
        except Exception as e:
            logging.error(f"Fatal error handling client {self.address}: {e}")
        finally:
            try:
                self.connection.close()
            except:
                pass
            logging.info(f"Connection with {self.address} closed")

class Server(threading.Thread):
    def __init__(self, ipaddress='0.0.0.0', port=6666):
        self.ipinfo = (ipaddress, port)
        self.the_clients = []
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        threading.Thread.__init__(self)

    def run(self):
        try:
            logging.info(f"Multithreading server running on {self.ipinfo}")
            self.my_socket.bind(self.ipinfo)
            self.my_socket.listen(100)  # Increased backlog
            
            while True:
                self.connection, self.client_address = self.my_socket.accept()
                logging.info(f"New connection from {self.client_address}")

                clt = ProcessTheClient(self.connection, self.client_address)
                clt.start()
                self.the_clients.append(clt)
                
                # Clean up finished threads more frequently
                if len(self.the_clients) > 50:
                    self.the_clients = [t for t in self.the_clients if t.is_alive()]
                
        except KeyboardInterrupt:
            logging.info("Server shutdown requested")
            sys.exit(0)
        except Exception as e:
            logging.error(f"Server error: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        for client in self.the_clients:
            if client.is_alive():
                client.join(timeout=1)
        self.my_socket.close()
        logging.info("Multithreading server cleaned up")

def main():
    # Pastikan folder files ada
    if not os.path.exists('files'):
        os.makedirs('files')
        print("Created 'files' directory")
    
    svr = Server(ipaddress='0.0.0.0', port=6666)
    svr.start()
    
    try:
        # Keep main thread alive
        while svr.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down server...")
        sys.exit(0)

if __name__ == "__main__":
    main()