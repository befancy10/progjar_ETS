# progjar_ETS

# Tugas ETS - Pemrograman Jaringan

## Deskripsi Tugas

1. Dari hasil modifikasi program [TUGAS 3](https://github.com/rm77/progjar/tree/master/progjar4a), lakukan pengembangan lebih lanjut.

2. **Ubah model pemrosesan concurrency** dari yang ada menjadi:
   - a. **Multithreading menggunakan pool**
   - b. **Multiprocessing menggunakan pool**

3. **Modifikasi program client** agar dapat melakukan:
   - a. Download file
   - b. Upload file
   - c. List file

4. **Lakukan stress test** pada program server dengan cara membuat client melakukan proses nomor 3 secara concurrent menggunakan:
   - Multithreading pool
   - Multiprocessing pool

### Kombinasi Stress Test
- Operasi: `download`, `upload`
- Volume file: `10 MB`, `50 MB`, `100 MB`
- Jumlah client worker pool: `1`, `5`, `50`
- Jumlah server worker pool: `1`, `5`, `50`

### Catatan untuk setiap kombinasi:
- **A.** Waktu total per client melakukan proses upload/download (dalam detik)
- **B.** Throughput per client (dalam bytes per second, total bytes yang sukses diproses per second)
- **C.** Jumlah worker client yang sukses dan gagal
- **D.** Jumlah worker server yang sukses dan gagal

5. **Hasil stress test dirangkum ke dalam tabel**, setiap baris adalah satu kombinasi.
   - Total kombinasi: `2 (operasi) x 3 (volume file) x 3 (jumlah client worker) x 3 (jumlah server worker) = 81 kombinasi`

---

> **Catatan**: Pastikan semua percobaan dilakukan untuk kedua model concurrency: **Multithreading Pool** dan **Multiprocessing Pool**.
