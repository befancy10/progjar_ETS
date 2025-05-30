import socket
import multiprocessing as mp
import logging
import signal
from file_protocol import FileProtocol

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def handle_client_process(connection, address):
    """Handle client in separate process"""
    try:
        fp = FileProtocol()
        logging.info(f"Process {mp.current_process().pid} handling client {address}")
        
        # Receive data with larger buffer
        data = connection.recv(8192)
        if data:
            d = data.decode('utf-8')
            hasil = fp.proses_string(d)
            hasil = hasil + "\r\n\r\n"
            connection.sendall(hasil.encode('utf-8'))
            
    except Exception as e:
        logging.error(f"Error in process handling {address}: {e}")
    finally:
        connection.close()
        logging.info(f"Process {mp.current_process().pid} finished handling {address}")

class MultiprocessingServer:
    def __init__(self, ipaddress='0.0.0.0', port=6666, max_processes=5):
        self.ipinfo = (ipaddress, port)
        self.max_processes = max_processes
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.processes = []
        self.running = True
        
        # Setup signal handlers (tanpa sys)
        signal.signal(signal.SIGINT, self.signal_handler)
        try:
            signal.signal(signal.SIGTERM, self.signal_handler)
        except AttributeError:
            # SIGTERM mungkin tidak tersedia di Windows
            pass

    def signal_handler(self, signum, frame):
        logging.info(f"Received signal {signum}, shutting down...")
        self.running = False

    def run(self):
        try:
            self.my_socket.bind(self.ipinfo)
            self.my_socket.listen(50)  # Increased backlog
            self.my_socket.settimeout(1.0)  # Non-blocking accept
            logging.info(f"Multiprocessing Server running on {self.ipinfo} with max {self.max_processes} processes")

            while self.running:
                try:
                    connection, address = self.my_socket.accept()
                    logging.info(f"New connection from {address}")
                    
                    # Clean up finished processes
                    self.processes = [p for p in self.processes if p.is_alive()]
                    
                    # Create new process if under limit
                    if len(self.processes) < self.max_processes:
                        process = mp.Process(target=handle_client_process, args=(connection, address))
                        process.start()
                        self.processes.append(process)
                        logging.info(f"Started new process {process.pid} for {address}")
                        
                        # Close connection in parent process
                        connection.close()
                    else:
                        logging.warning(f"Max processes ({self.max_processes}) reached, rejecting connection from {address}")
                        connection.close()
                        
                except socket.timeout:
                    continue  # Check if still running
                except Exception as e:
                    if self.running:
                        logging.error(f"Accept error: {e}")
                    
        except KeyboardInterrupt:
            logging.info("Server shutdown requested")
        except Exception as e:
            logging.error(f"Server error: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        logging.info("Starting cleanup...")
        self.running = False
        
        for process in self.processes:
            if process.is_alive():
                logging.info(f"Terminating process {process.pid}")
                process.terminate()
                process.join(timeout=2)
                if process.is_alive():
                    logging.warning(f"Force killing process {process.pid}")
                    process.kill()
        
        try:
            self.my_socket.close()
        except:
            pass
        
        logging.info("Multiprocessing Server cleaned up")

def main():
    # Pastikan folder files ada
    import os
    if not os.path.exists('files'):
        os.makedirs('files')
        print("Created 'files' directory")
    
    server = MultiprocessingServer(max_processes=50)  # Increased for stress test
    
    try:
        server.run()
    except KeyboardInterrupt:
        print("Server interrupted")
    finally:
        server.cleanup()

if __name__ == "__main__":
    main()