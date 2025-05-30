import json
import logging
import shlex
import threading
import base64

from file_interface import FileInterface

class FileProtocol:
    def __init__(self):
        # Create thread-local storage for FileInterface untuk thread safety
        self._local = threading.local()
    
    def get_file_interface(self):
        """Get thread-local FileInterface instance"""
        if not hasattr(self._local, 'file'):
            # Pastikan FileInterface menggunakan folder files untuk server
            self._local.file = FileInterface('files')
        return self._local.file
    
    def proses_string(self, string_datamasuk=''):
        # Limit log untuk file besar - hanya tampilkan awal command
        command_preview = string_datamasuk[:50] + "..." if len(string_datamasuk) > 50 else string_datamasuk
        logging.info(f"Processing command: {command_preview}")
        
        try:
            # Clean input string
            string_datamasuk = string_datamasuk.strip()
            if not string_datamasuk:
                return json.dumps(dict(status='ERROR', message='Empty request'))
            
            # Handle UPLOAD command khusus karena mengandung base64 data yang panjang
            if string_datamasuk.upper().startswith('UPLOAD'):
                # Split manual untuk UPLOAD: UPLOAD filename base64data
                parts = string_datamasuk.split(' ', 2)
                if len(parts) >= 3:
                    c_request = parts[0].strip().lower()
                    filename = parts[1].strip()
                    file_content = parts[2]  # Jangan di-strip, ini base64 data
                    
                    # Validate base64 content
                    try:
                        base64.b64decode(file_content)  # Test if valid base64
                        params = [filename, file_content]
                    except Exception as e:
                        logging.error(f"Invalid base64 content: {e}")
                        return json.dumps(dict(status='ERROR', message='Invalid file content encoding'))
                        
                elif len(parts) == 2:
                    c_request = parts[0].strip().lower()
                    filename = parts[1].strip()
                    params = [filename, '']  # Empty file content
                else:
                    return json.dumps(dict(status='ERROR', message='UPLOAD command incomplete'))
            else:
                # Gunakan shlex untuk command lainnya
                try:
                    c = shlex.split(string_datamasuk.lower())
                    c_request = c[0].strip() if c else ''
                    params = [x.strip() for x in c[1:]] if len(c) > 1 else []
                except ValueError as e:
                    # Jika shlex gagal (misalnya quote tidak seimbang), fallback ke split biasa
                    logging.warning(f"shlex parse failed, using simple split: {e}")
                    parts = string_datamasuk.split()
                    c_request = parts[0].lower() if parts else ''
                    params = parts[1:] if len(parts) > 1 else []
            
            if not c_request:
                return json.dumps(dict(status='ERROR', message='Empty command'))
            
            logging.info(f"Executing command: {c_request}")
            
            # Get thread-local file interface
            file_interface = self.get_file_interface()
            
            # Execute command
            if hasattr(file_interface, c_request):
                method = getattr(file_interface, c_request)
                try:
                    cl = method(params)
                    return json.dumps(cl)
                except Exception as e:
                    logging.error(f"Error executing {c_request}: {e}")
                    return json.dumps(dict(status='ERROR', message=f'Error executing command: {str(e)}'))
            else:
                return json.dumps(dict(status='ERROR', message=f'Unknown command: "{c_request}"'))
                
        except Exception as e:
            logging.error(f"Error processing request: {e}")
            return json.dumps(dict(status='ERROR', message='Request processing failed'))

if __name__ == '__main__':
    # Setup logging untuk testing
    logging.basicConfig(level=logging.INFO)
    
    # Test protocol
    fp = FileProtocol()
    
    print("Testing FileProtocol:")
    print("1. LIST command:")
    print(fp.proses_string("LIST"))
    
    print("\n2. GET command:")
    print(fp.proses_string("GET test.txt"))
    
    print("\n3. DELETE command:")
    print(fp.proses_string("DELETE test.txt"))
    
    print("\n4. UPLOAD command:")
    print(fp.proses_string("UPLOAD test.txt dGVzdCBkYXRh"))  # "test data" in base64