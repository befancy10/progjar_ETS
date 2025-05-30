import socket
import json
import base64
import logging
import os
import time

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

server_address = ('localhost', 6666)

def send_command(command_str=""):
    global server_address
    max_retries = 3
    
    for attempt in range(max_retries):
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # Set socket options untuk performa yang lebih baik
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
            sock.settimeout(120)  # 2 menit timeout
            
            sock.connect(server_address)
            logging.info(f"Connected to {server_address} (attempt {attempt + 1})")
            
            # Send command
            command_bytes = command_str.encode('utf-8')
            total_sent = 0
            chunk_size = 32768
            
            # Send in chunks untuk command besar
            for i in range(0, len(command_bytes), chunk_size):
                chunk = command_bytes[i:i + chunk_size]
                sock.sendall(chunk)
                total_sent += len(chunk)
                
                # Progress untuk upload besar
                if total_sent % (1024 * 1024) == 0:
                    logging.info(f"Sent {total_sent // (1024*1024)}MB")
            
            logging.info(f"Command sent successfully ({total_sent} bytes)")
            
            # Receive response
            data_received = b""
            while True:
                try:
                    chunk = sock.recv(32768)
                    if chunk:
                        data_received += chunk
                        # Check for protocol terminator
                        if b"\r\n\r\n" in data_received:
                            break
                    else:
                        break
                except socket.timeout:
                    logging.warning("Timeout receiving response")
                    break
            
            # Process response
            if data_received:
                response_str = data_received.decode('utf-8', errors='ignore')
                response_str = response_str.replace("\r\n\r\n", "")
                
                if response_str.strip():
                    try:
                        hasil = json.loads(response_str)
                        logging.info("Response received successfully")
                        return hasil
                    except json.JSONDecodeError as e:
                        logging.error(f"JSON decode error: {e}")
                        return {'status': 'ERROR', 'message': f'Invalid response format: {e}'}
                else:
                    return {'status': 'ERROR', 'message': 'Empty response'}
            else:
                return {'status': 'ERROR', 'message': 'No response received'}
            
        except socket.timeout:
            logging.warning(f"Timeout on attempt {attempt + 1}")
            if attempt == max_retries - 1:
                return {'status': 'ERROR', 'message': 'Connection timeout'}
        except ConnectionRefusedError:
            logging.warning(f"Connection refused on attempt {attempt + 1}")
            if attempt == max_retries - 1:
                return {'status': 'ERROR', 'message': 'Server not available'}
        except Exception as e:
            logging.warning(f"Error on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                return {'status': 'ERROR', 'message': str(e)}
        finally:
            if sock:
                try:
                    sock.close()
                except:
                    pass
        
        time.sleep(1)  # Wait before retry
    
    return {'status': 'ERROR', 'message': 'Max retries exceeded'}

def remote_list():
    command_str = "LIST"
    hasil = send_command(command_str)
    if hasil and hasil.get('status') == 'OK':
        print("\nDaftar file di server:")
        for nmfile in hasil['data']:
            print(f"- {nmfile}")
        return True
    else:
        error_msg = hasil.get('message', 'Unknown error') if hasil else 'Connection failed'
        print(f"Gagal mendapatkan daftar file: {error_msg}")
        return False

def remote_get(filename=""):
    command_str = f"GET {filename}"
    hasil = send_command(command_str)
    if hasil and hasil.get('status') == 'OK':
        try:
            namafile = hasil['data_namafile']
            isifile = base64.b64decode(hasil['data_file'])
            
            safe_filename = os.path.basename(namafile)
            with open(safe_filename, 'wb') as fp:
                fp.write(isifile)
            
            print(f"File {safe_filename} berhasil didownload ({len(isifile)} bytes)")
            return True
        except Exception as e:
            print(f"Error processing downloaded file: {e}")
            return False
    else:
        error_msg = hasil.get('message', 'Unknown error') if hasil else 'Connection failed'
        print(f"Gagal download file {filename}: {error_msg}")
        return False

def remote_upload(filename=""):
    if not os.path.exists(filename):
        print(f"File {filename} tidak ditemukan")
        return False
    
    try:
        file_size = os.path.getsize(filename)
        
        # Check file size limit
        max_size = 50 * 1024 * 1024  # 50MB limit untuk testing
        if file_size > max_size:
            print(f"File terlalu besar ({file_size} bytes). Maksimal {max_size} bytes")
            return False
        
        print(f"Uploading file {filename} ({file_size} bytes)...")
        
        # Read and encode file
        with open(filename, 'rb') as fp:
            file_content = base64.b64encode(fp.read()).decode('utf-8')
        
        filename_only = os.path.basename(filename)
        command_str = f"UPLOAD {filename_only} {file_content}"
        
        print(f"Sending command ({len(command_str)} chars)...")
        hasil = send_command(command_str)
        
        if hasil and hasil.get('status') == 'OK':
            print(f"File {filename_only} berhasil diupload")
            return True
        else:
            error_msg = hasil.get('message', 'Unknown error') if hasil else 'Connection failed'
            print(f"Gagal upload file: {error_msg}")
            return False
            
    except MemoryError:
        print("Error: File terlalu besar untuk dimuat ke memory")
        return False
    except Exception as e:
        print(f"Error during upload: {e}")
        return False

def remote_delete(filename=""):
    command_str = f"DELETE {filename}"
    hasil = send_command(command_str)
    if hasil and hasil.get('status') == 'OK':
        print(f"File {filename} berhasil dihapus")
        return True
    else:
        error_msg = hasil.get('message', 'Unknown error') if hasil else 'Connection failed'
        print(f"Gagal menghapus file: {error_msg}")
        return False

def show_menu():
    print("\n=== FILE SERVER MENU ===")
    print("1. List File")
    print("2. Download File")
    print("3. Upload File")
    print("4. Delete File")
    print("0. Exit")
    print("----------------------")

if __name__ == '__main__':
    server_address = ('localhost', 6666)
    
    while True:
        show_menu()
        try:
            choice = input("Pilih menu (0-4): ").strip()
            
            if choice == "1":
                remote_list()
            
            elif choice == "2":
                if remote_list():
                    filename = input("Masukkan nama file yang akan didownload: ").strip()
                    if filename:
                        remote_get(filename)
            
            elif choice == "3":
                filename = input("Masukkan path file yang akan diupload: ").strip()
                if filename:
                    remote_upload(filename)
            
            elif choice == "4":
                if remote_list():
                    filename = input("Masukkan nama file yang akan dihapus: ").strip()
                    if filename:
                        remote_delete(filename)
            
            elif choice == "0":
                print("Terima kasih telah menggunakan layanan file server")
                break
            
            else:
                print("Pilihan tidak valid!")
                
        except KeyboardInterrupt:
            print("\nProgram dihentikan oleh user")
            break
        except Exception as e:
            print(f"Terjadi kesalahan: {str(e)}")
            print("Silakan coba lagi")