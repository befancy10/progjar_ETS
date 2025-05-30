import os
import json
import base64
from glob import glob
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)

class FileInterface:
    def __init__(self, base_path='files'):
        try:
            self.base_path = base_path
            # Pastikan folder files ada tapi JANGAN ubah working directory
            if not os.path.exists(self.base_path):
                os.makedirs(self.base_path)
            logging.info(f"FileInterface initialized, base path: {self.base_path}")
        except Exception as e:
            logging.error(f"Error initializing FileInterface: {e}")
            raise

    def _get_file_path(self, filename):
        """Get full path for file in base directory"""
        return os.path.join(self.base_path, filename)

    def list(self, params=[]):
        try:
            # Gunakan glob dengan path lengkap
            pattern = os.path.join(self.base_path, '*.*')
            full_paths = glob(pattern)
            # Ambil hanya nama file saja
            filelist = [os.path.basename(path) for path in full_paths]
            logging.info(f"Listed {len(filelist)} files from {self.base_path}")
            return dict(status='OK', data=filelist)
        except Exception as e:
            logging.error(f"Error listing files: {e}")
            return dict(status='ERROR', message=str(e))

    def get(self, params=[]):
        try:
            if not params or params[0] == '':
                return dict(status='ERROR', message='Filename required')
            
            filename = params[0]
            filepath = self._get_file_path(filename)
            
            if not os.path.exists(filepath):
                return dict(status='ERROR', message='File not found')
            
            # Check file size
            file_size = os.path.getsize(filepath)
            max_size = 100 * 1024 * 1024  # 100MB limit
            
            if file_size > max_size:
                return dict(status='ERROR', message=f'File too large ({file_size} bytes)')
            
            with open(filepath, 'rb') as fp:
                file_content = fp.read()
                isifile = base64.b64encode(file_content).decode()
            
            logging.info(f"File {filename} retrieved ({file_size} bytes)")
            return dict(status='OK', data_namafile=filename, data_file=isifile)
            
        except Exception as e:
            logging.error(f"Error getting file: {e}")
            return dict(status='ERROR', message=str(e))
    
    def upload(self, params=[]):
        try:
            if len(params) < 2:
                return dict(status='ERROR', message='Filename and content required')
            
            filename = params[0]
            file_content_b64 = params[1]
            
            if not filename:
                return dict(status='ERROR', message='Filename required')
            
            if not file_content_b64:
                return dict(status='ERROR', message='File content required')
            
            # Decode base64 content
            try:
                file_content = base64.b64decode(file_content_b64)
            except Exception as e:
                return dict(status='ERROR', message=f'Invalid base64 encoding: {str(e)}')
            
            # Check decoded size
            max_size = 100 * 1024 * 1024  # 100MB limit
            if len(file_content) > max_size:
                return dict(status='ERROR', message=f'File too large ({len(file_content)} bytes)')
            
            # Write file dengan path lengkap
            filepath = self._get_file_path(filename)
            with open(filepath, 'wb') as fp:
                fp.write(file_content)
            
            logging.info(f"File {filename} uploaded ({len(file_content)} bytes)")
            return dict(status='OK', data_namafile=filename, message='File uploaded successfully')
            
        except Exception as e:
            logging.error(f"Error uploading file: {e}")
            return dict(status='ERROR', message=str(e))

    def delete(self, params=[]):
        try:
            if not params or params[0] == '':
                return dict(status='ERROR', message='Filename required')
            
            filename = params[0]
            filepath = self._get_file_path(filename)
            
            if not os.path.exists(filepath):
                return dict(status='ERROR', message='File not found')
            
            os.remove(filepath)
            logging.info(f"File {filename} deleted")
            return dict(status='OK', message='File deleted successfully')
            
        except Exception as e:
            logging.error(f"Error deleting file: {e}")
            return dict(status='ERROR', message=str(e))

if __name__ == '__main__':
    f = FileInterface()
    print("Testing FileInterface:")
    print("1. List files:", f.list())
    print("2. Upload test:", f.upload(['test.txt', 'dGVzdCBkYXRh']))  # "test data" in base64
    print("3. List files after upload:", f.list())
    print("4. Get test:", f.get(['test.txt']))
    print("5. Delete test:", f.delete(['test.txt']))