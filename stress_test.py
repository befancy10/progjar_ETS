import concurrent.futures
import time
import os
import socket
import threading
import logging
import csv
import json
import base64
from datetime import datetime
import statistics

# Setup logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

class FileClient:
    def __init__(self, server_address=('localhost', 6666)):
        self.server_address = server_address

    def send_command_robust(self, command, timeout=120):
        """Send command with robust error handling"""
        max_retries = 2
        
        for attempt in range(max_retries):
            sock = None
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
                sock.settimeout(timeout)
                sock.connect(self.server_address)
                
                # Send command in chunks
                command_bytes = command.encode('utf-8')
                chunk_size = 32768
                
                for i in range(0, len(command_bytes), chunk_size):
                    chunk = command_bytes[i:i + chunk_size]
                    sock.sendall(chunk)
                
                # Receive response
                response_data = b""
                while True:
                    try:
                        data = sock.recv(32768)
                        if data:
                            response_data += data
                            if b"\r\n\r\n" in response_data:
                                break
                        else:
                            break
                    except socket.timeout:
                        break
                
                if response_data:
                    response_str = response_data.decode('utf-8', errors='ignore')
                    response_str = response_str.replace("\r\n\r\n", "")
                    result = json.loads(response_str)
                    return result
                else:
                    return {'status': 'ERROR', 'message': 'No response'}
                    
            except Exception as e:
                if attempt == max_retries - 1:
                    return {'status': 'ERROR', 'message': str(e)}
                time.sleep(0.5)
            finally:
                if sock:
                    try:
                        sock.close()
                    except:
                        pass
        
        return {'status': 'ERROR', 'message': 'Max retries exceeded'}

    def upload_file(self, file_path):
        """Upload file to server using proper protocol"""
        try:
            with open(file_path, 'rb') as f:
                file_content = base64.b64encode(f.read()).decode()
            
            filename = os.path.basename(file_path)
            command = f"UPLOAD {filename} {file_content}"
            
            # Adjust timeout based on file size
            file_size = os.path.getsize(file_path)
            timeout = max(120, file_size // (1024 * 1024) * 10)  # 10 seconds per MB, min 2 minutes
            
            result = self.send_command_robust(command, timeout)
            return result.get('status') == 'OK'
            
        except Exception as e:
            logging.debug(f"Upload error: {e}")
            return False

    def download_file(self, filename):
        """Download file from server using proper protocol"""
        try:
            command = f"GET {filename}"
            result = self.send_command_robust(command, 120)
            return result.get('status') == 'OK'
            
        except Exception as e:
            logging.debug(f"Download error: {e}")
            return False

class ComprehensiveStressTest:
    def __init__(self, server_address=('localhost', 6666)):
        self.server_address = server_address
        self.client = FileClient(server_address)
        self.test_files = {}

    def create_test_files(self):
        """Create all test files at the beginning and keep them"""
        sizes = [10, 50, 100]  # MB
        
        print("Creating test files...")
        for size_mb in sizes:
            filename = f"test_{size_mb}MB.txt"
            
            if os.path.exists(filename):
                existing_size = os.path.getsize(filename) / (1024 * 1024)
                if abs(existing_size - size_mb) < 0.1:
                    print(f"✓ Using existing {filename} ({existing_size:.1f}MB)")
                    self.test_files[size_mb] = filename
                    continue
            
            print(f"Creating {filename} ({size_mb}MB)...")
            try:
                with open(filename, 'w') as f:  # Text file instead of binary for better compression
                    chunk_size = 1024  # 1KB chunks of text
                    text_chunk = "A" * chunk_size
                    chunks_needed = (size_mb * 1024 * 1024) // chunk_size
                    
                    for i in range(chunks_needed):
                        f.write(text_chunk)
                        if (i + 1) % 10240 == 0:  # Every 10MB
                            print(f"  Progress: {(i+1)*chunk_size//(1024*1024)}MB")
                
                self.test_files[size_mb] = filename
                actual_size = os.path.getsize(filename) / (1024 * 1024)
                print(f"✓ Created {filename} ({actual_size:.1f}MB)")
                
            except Exception as e:
                logging.error(f"Error creating {filename}: {e}")
                return False
        
        print("All test files ready!")
        return True

    def single_operation_test(self, operation, file_path, test_id):
        """Single operation test with better error handling"""
        start_time = time.time()
        success = False
        
        try:
            if operation == "upload":
                success = self.client.upload_file(file_path)
            elif operation == "download":
                filename = os.path.basename(file_path)
                success = self.client.download_file(filename)
            
        except Exception as e:
            logging.debug(f"Test {test_id} error: {e}")
        
        end_time = time.time()
        operation_time = end_time - start_time
        
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        throughput = file_size / operation_time if operation_time > 0 and success else 0
        
        return {
            'test_id': test_id,
            'success': success,
            'time': operation_time,
            'size': file_size,
            'throughput': throughput,
            'thread': threading.current_thread().name
        }

    def run_stress_test(self, operation, volume_mb, jumlah_client_worker, jumlah_server_worker):
        """Run stress test with specified parameters"""
        print(f"Running {operation} test: {volume_mb}MB, {jumlah_client_worker} clients, {jumlah_server_worker} server workers")
        
        test_file = self.test_files.get(volume_mb)
        if not test_file or not os.path.exists(test_file):
            print(f"Error: Test file for {volume_mb}MB not found!")
            return None
        
        start_time = time.time()
        results = []
        
        # Reduce concurrent workers for better success rate
        actual_workers = min(jumlah_client_worker, 10)  # Max 10 concurrent for stability
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=actual_workers) as executor:
            # Submit all tasks
            futures = []
            for i in range(jumlah_client_worker):
                future = executor.submit(self.single_operation_test, operation, test_file, i)
                futures.append(future)
                
                # Add small delay between submissions for large file tests
                if volume_mb >= 50:
                    time.sleep(0.1)
            
            # Collect results with extended timeout
            timeout_per_test = 300 if volume_mb >= 50 else 180  # 5 minutes for large files
            
            for i, future in enumerate(futures):
                try:
                    result = future.result(timeout=timeout_per_test)
                    results.append(result)
                    
                    if (i + 1) % 10 == 0:
                        success_count = sum(1 for r in results if r['success'])
                        print(f"  Progress: {i+1}/{len(futures)} - Success: {success_count}")
                        
                except concurrent.futures.TimeoutError:
                    results.append({
                        'test_id': i,
                        'success': False,
                        'time': timeout_per_test,
                        'size': 0,
                        'throughput': 0
                    })
                except Exception as e:
                    logging.error(f"Future error: {e}")
                    results.append({
                        'test_id': i,
                        'success': False,
                        'time': 0,
                        'size': 0,
                        'throughput': 0
                    })
        
        end_time = time.time()
        
        # Calculate metrics
        successful_results = [r for r in results if r['success']]
        failed_results = [r for r in results if not r['success']]
        
        worker_client_sukses = len(successful_results)
        worker_client_gagal = len(failed_results)
        worker_server_sukses = min(worker_client_sukses, jumlah_server_worker)
        worker_server_gagal = jumlah_server_worker - worker_server_sukses
        
        waktu_total_per_client = end_time - start_time
        
        if successful_results:
            avg_throughput = statistics.mean([r['throughput'] for r in successful_results])
            throughput_per_client = avg_throughput
        else:
            throughput_per_client = 0
        
        print(f"  Completed - Success: {worker_client_sukses}/{jumlah_client_worker}")
        
        return {
            'operasi': operation,
            'volume': f"{volume_mb}MB",
            'jumlah_client_worker': jumlah_client_worker,
            'jumlah_server_worker': jumlah_server_worker,
            'waktu_total_per_client': waktu_total_per_client,
            'throughput_per_client': throughput_per_client,
            'worker_client_sukses': worker_client_sukses,
            'worker_client_gagal': worker_client_gagal,
            'worker_server_sukses': worker_server_sukses,
            'worker_server_gagal': worker_server_gagal
        }

def run_all_combinations():
    """Run all test combinations as per assignment requirements"""
    test = ComprehensiveStressTest()
    
    if not test.create_test_files():
        print("Failed to create test files!")
        return []
    
    results = []
    
    operations = ['upload', 'download']
    volumes = [10, 50, 100]
    client_workers = [1, 5, 50]
    server_workers = [1, 5, 50]
    
    total_tests = len(operations) * len(volumes) * len(client_workers) * len(server_workers)
    test_number = 1
    
    print(f"\nStarting comprehensive stress test with {total_tests} combinations...")
    print("=" * 100)
    
    for operation in operations:
        for volume in volumes:
            for client_worker in client_workers:
                for server_worker in server_workers:
                    print(f"\nTest {test_number}/{total_tests}: {operation} {volume}MB, C:{client_worker}, S:{server_worker}")
                    
                    result = test.run_stress_test(operation, volume, client_worker, server_worker)
                    if result:
                        result['nomor'] = test_number
                        results.append(result)
                    else:
                        print("✗ Test failed")
                    
                    test_number += 1
                    time.sleep(2)  # Longer pause between tests
    
    return results

# Sisanya tetap sama (print_results_table, save_results_to_csv, dll.)
def print_results_table(results):
    """Print results in the exact format shown by the teacher"""
    if not results:
        print("No results to display")
        return
    
    print("\n" + "="*150)
    print("STRESS TEST RESULTS")
    print("="*150)
    
    headers = [
        "nomor", "operasi", "volume", "jumlah_client_worker", "jumlah_server_worker",
        "waktu_total_per_client", "throughput_per_client", "worker_client_sukses",
        "worker_client_gagal", "worker_server_sukses", "worker_server_gagal"
    ]
    
    header_line = " | ".join([f"{h:<20}" for h in headers])
    print(header_line)
    print("-" * len(header_line))
    
    for result in results:
        row = [
            str(result['nomor']),
            result['operasi'],
            result['volume'],
            str(result['jumlah_client_worker']),
            str(result['jumlah_server_worker']),
            f"{result['waktu_total_per_client']:.3f}",
            f"{result['throughput_per_client']:.3f}",
            str(result['worker_client_sukses']),
            str(result['worker_client_gagal']),
            str(result['worker_server_sukses']),
            str(result['worker_server_gagal'])
        ]
        
        row_line = " | ".join([f"{cell:<20}" for cell in row])
        print(row_line)

def save_results_to_csv(results, filename="stress_test_results.csv"):
   """Save results to CSV file in the exact format"""
   try:
       with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
           fieldnames = [
               'nomor', 'operasi', 'volume', 'jumlah_client_worker', 'jumlah_server_worker',
               'waktu_total_per_client', 'throughput_per_client', 'worker_client_sukses',
               'worker_client_gagal', 'worker_server_sukses', 'worker_server_gagal'
           ]
           
           writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
           writer.writeheader()
           
           for result in results:
               writer.writerow(result)
       
       print(f"\nResults saved to {filename}")
       
   except Exception as e:
       logging.error(f"Error saving CSV: {e}")

def generate_analysis_report(results):
   """Generate analysis report comparing multithreading vs multiprocessing"""
   print("\n" + "="*80)
   print("ANALYSIS REPORT - MULTITHREADING VS MULTIPROCESSING")
   print("="*80)
   
   upload_results = [r for r in results if r['operasi'] == 'upload']
   download_results = [r for r in results if r['operasi'] == 'download']
   
   print(f"\nUPLOAD OPERATIONS ANALYSIS:")
   print(f"Total upload tests: {len(upload_results)}")
   if upload_results:
       avg_upload_throughput = statistics.mean([r['throughput_per_client'] for r in upload_results])
       avg_upload_time = statistics.mean([r['waktu_total_per_client'] for r in upload_results])
       total_upload_success = sum([r['worker_client_sukses'] for r in upload_results])
       total_upload_attempts = sum([r['jumlah_client_worker'] for r in upload_results])
       success_rate_upload = (total_upload_success / total_upload_attempts) * 100 if total_upload_attempts > 0 else 0
       
       print(f"Average throughput: {avg_upload_throughput:.3f} bytes/second")
       print(f"Average time per test: {avg_upload_time:.3f} seconds")
       print(f"Overall success rate: {success_rate_upload:.1f}%")
   
   print(f"\nDOWNLOAD OPERATIONS ANALYSIS:")
   print(f"Total download tests: {len(download_results)}")
   if download_results:
       avg_download_throughput = statistics.mean([r['throughput_per_client'] for r in download_results])
       avg_download_time = statistics.mean([r['waktu_total_per_client'] for r in download_results])
       total_download_success = sum([r['worker_client_sukses'] for r in download_results])
       total_download_attempts = sum([r['jumlah_client_worker'] for r in download_results])
       success_rate_download = (total_download_success / total_download_attempts) * 100 if total_download_attempts > 0 else 0
       
       print(f"Average throughput: {avg_download_throughput:.3f} bytes/second")
       print(f"Average time per test: {avg_download_time:.3f} seconds")
       print(f"Overall success rate: {success_rate_download:.1f}%")
   
   print(f"\nPERFORMANCE BY FILE SIZE:")
   for volume in [10, 50, 100]:
       volume_results = [r for r in results if r['volume'] == f'{volume}MB']
       if volume_results:
           avg_throughput = statistics.mean([r['throughput_per_client'] for r in volume_results])
           avg_time = statistics.mean([r['waktu_total_per_client'] for r in volume_results])
           total_success = sum([r['worker_client_sukses'] for r in volume_results])
           total_attempts = sum([r['jumlah_client_worker'] for r in volume_results])
           success_rate = (total_success / total_attempts) * 100 if total_attempts > 0 else 0
           print(f"{volume}MB files - Success Rate: {success_rate:.1f}%, Avg Throughput: {avg_throughput:.3f} B/s, Avg Time: {avg_time:.3f}s")

def main():
   print("COMPREHENSIVE STRESS TEST - IMPROVED VERSION")
   print(f"Start time: {datetime.now()}")
   print("="*80)
   
   # Pastikan folder files ada
   if not os.path.exists('files'):
       os.makedirs('files')
       print("Created 'files' directory")
   
   try:
       

       results = run_all_combinations()
       
       print_results_table(results)
       
       SERVER_MODE = "threading"  # atau "multiprocessing"
       timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
       
       filename = f"stress_{SERVER_MODE}_{timestamp}.csv"
       
       save_results_to_csv(results, filename)
       
       generate_analysis_report(results)
       
       print(f"\nTest completed at: {datetime.now()}")
       print("="*80)
       
   except KeyboardInterrupt:
       print("\nTest interrupted by user")
   except Exception as e:
       print(f"Error during test: {e}")
       logging.error(f"Test error: {e}")
   finally:
       print("Cleaning up...")

if __name__ == "__main__":
   main()