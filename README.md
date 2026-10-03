# NgertiBareng

AI Agent yang membantu lansia memahami surat resmi dan layanan publik (BPJS, bantuan sosial, pajak) dalam **Bahasa Jawa sederhana**, disertai terjemahan Bahasa Indonesia dan checklist langkah tindakan.

> Teknologi AI sering meninggalkan orang yang paling butuh bantuan. NgertiBareng membawa layanan publik ke bahasa yang dipahami lansia, bukan memaksa mereka belajar bahasa teknologi.

Dibuat oleh tim **jujucimol** untuk hackathon **IBM SkillsBuild**.

---

## Masalah

Surat resmi ditulis dalam bahasa Indonesia formal yang sulit dipahami banyak lansia, terutama penutur bahasa daerah yang kurang akrab dengan teknologi. Akibatnya mereka salah mengartikan isi surat, terlambat bertindak, atau bergantung pada orang lain, dan berisiko kehilangan layanan (misalnya kepesertaan BPJS tidak aktif karena tunggakan).

## Solusi

Pengguna mengunggah foto, PDF, atau mengetik isi surat. NgertiBareng menampilkan:

- Penjelasan **Bahasa Jawa sederhana** + terjemahan **Bahasa Indonesia**
- **Poin penting**: jenis surat, tingkat urgensi, nominal, status, batas waktu
- **Checklist tindakan** dan dokumen yang perlu dibawa
- **Tanya jawab lanjutan** seperti ngobrol biasa
- Mode **tulisan besar** untuk kenyamanan lansia

## Skenario demo

Seorang nenek menerima surat tunggakan iuran BPJS. Surat difoto dan diunggah, lalu aplikasi menjelaskan maksudnya dalam Bahasa Jawa dan memberi langkah konkret yang harus dilakukan.

## Arsitektur

Pengguna (foto / PDF / teks)
|
Aplikasi Streamlit (app.py, prompt.py)
|
+-- Teks dan PDF --> IBM Langflow (Chat Input -> Agent Gemini -> Chat Output)
|
+-- Foto dan tanya jawab lanjutan --> Gemini API (langsung)
|
Hasil terstruktur (JSON) --> tampilan Jawa + Indonesia + checklist


## Peran IBM Langflow

Langflow adalah lapisan orkestrasi AI. Flow **Chat Input -> Agent -> Chat Output** memakai model Gemini dengan instruksi khusus NgertiBareng, dan dipanggil aplikasi lewat API (Flow ID, API key, session ID). Keluarannya berupa JSON terstruktur: ringkasan dua bahasa, poin penting, checklist langkah, dokumen yang dibawa, dan pengingat batas waktu. Logika agen dapat diubah di Langflow tanpa mengubah kode aplikasi.

## Peran IBM Bob

IBM Bob dipakai pada **tahap pengembangan** (bukan saat aplikasi berjalan) untuk meninjau proyek dalam mode Plan: meringkas arsitektur dan menyusun daftar risiko (keamanan, kegagalan koneksi, akurasi). File `.env` dipindahkan keluar folder selama sesi dan Bob diminta tidak membacanya.

**Temuan Bob dan tindak lanjut:** [ISI: tulis 2-3 temuan nyata dari sesi Bob, lalu hapus tanda kurung ini]

## Menjalankan secara lokal

1. Salin `.env.example` menjadi `.env` lalu isi kunci milik Anda (jangan pernah commit `.env`).
2. Pasang dependensi: `streamlit`, `requests`, `python-dotenv`, dan pustaka Gemini yang dipakai `app.py`.
3. Jalankan Langflow dan siapkan flow agen NgertiBareng, lalu isi `LANGFLOW_URL`, `LANGFLOW_FLOW_ID`, `LANGFLOW_API_KEY` di `.env`.
4. Jalankan aplikasi: `streamlit run app.py`

## Pengujian otomatis

`test_ngertibareng.py` (pytest) memanggil flow Langflow dan memeriksa: respons berformat JSON, fakta penting (nominal dan batas waktu), tidak ada angka Rupiah karangan, keberadaan Bahasa Jawa dan terjemahan Indonesia, daftar langkah tindakan, kunci API tidak bocor, tanya jawab lanjutan, serta penanganan input kosong.

Jalankan: `python -m pytest test_ngertibareng.py -v`

## Batasan yang kami sadari

- Kualitas bahasa daerah **masih dalam validasi** dengan penutur asli.
- NgertiBareng adalah pendamping memahami surat, **bukan pengganti petugas resmi**; untuk keputusan penting, pengguna tetap dianjurkan memastikan ke instansi terkait.
- Langflow saat ini berjalan lokal; penggunaan dibatasi kuota API Gemini.
- Saat ini baru Bahasa Jawa; bahasa daerah lain direncanakan.

## Tim

jujucimol - [ISI: nama anggota]
