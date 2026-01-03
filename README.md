# Sistem Penggajian Sekolah

Implementasi SRS Sistem Penggajian Sekolah berbasis Django + Bootstrap untuk milestone Admin Sekolah.

## Fitur
- Autentikasi bawaan Django dengan peran Admin Sekolah.
- Manajemen master data pegawai dan komponen gaji.
- Manajemen periode gaji (draft/final) dengan constraint satu periode per bulan per sekolah.
- Generate payroll dengan tiga metode: manual (komponen aktif), copy dari periode final, dan impor Excel (`email,component_code,amount`).
- Penyesuaian nilai komponen selama status draft.
- Slip gaji per pegawai dapat diunduh ke PDF.
- Pencatatan waktu generate/finalisasi dan penjagaan histori.
- Perintah `seed_demo` untuk menyiapkan data contoh (admin: `admin/admin123`).

## Menjalankan Aplikasi
1. Instal dependensi:
   ```bash
   pip install -r requirements.txt
   ```
2. Jalankan migrasi database:
   ```bash
   python manage.py migrate
   ```
3. (Opsional) Buat data contoh:
   ```bash
   python manage.py seed_demo
   ```
4. Jalankan server:
   ```bash
   python manage.py runserver
   ```
5. Masuk ke antarmuka admin sekolah di `/accounts/login/` menggunakan kredensial hasil seeding atau akun yang Anda buat sendiri.

## Catatan
- Template Excel impor wajib memiliki header `email`, `component_code`, dan `amount`.
- Slip gaji PDF dibuat dengan ReportLab dan dapat diunduh dari halaman detail gaji pegawai.
- Untuk menambahkan pegawai/komponen baru cukup melalui menu masing-masing setelah login.
"# payroll-mvp" 
"# payroll-mvp" 
"# payroll-mvp" 
"# payroll-mvp" 
