import base64
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

from prompt import SYSTEM_PROMPT, CHAT_PROMPT, prompt_dengan_bahasa

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-3.5-flash-lite"

IKON = "icon.png" if os.path.exists("icon.png") else "📨"
st.set_page_config(page_title="NgertiBareng", page_icon=IKON, layout="wide")

# ---------- Surat contoh (semua fiktif) ----------
SURAT_BPJS = """BPJS KESEHATAN
Kantor Cabang Salatiga
Nomor: 1247/KCS-SLT/TGK/IX/2026
Tanggal: 22 September 2026
Perihal: Pemberitahuan Tunggakan Iuran Jaminan Kesehatan Nasional

Yth. Bapak/Ibu Suminem
(Kepala Keluarga a.n. Sarjono)
Dusun Krajan RT 02/RW 01, Desa Sidorejo, Kec. Contoh, Kab. Semarang
No. Kartu JKN: 0001234567890

Berdasarkan data kami, iuran JKN Segmen PBPU Kelas 3 atas nama peserta berikut BELUM DIBAYARKAN dan tercatat menunggak:
1. SUMINEM, Jun - Sep 2026, 4 bulan, Rp140.000
2. SARJONO, Jun - Sep 2026, 4 bulan, Rp140.000
TOTAL YANG HARUS DIBAYAR: Rp280.000

Akibat tunggakan tersebut, status kepesertaan Bapak/Ibu saat ini DINONAKTIFKAN SEMENTARA sehingga belum dapat digunakan untuk mendapatkan pelayanan kesehatan.

Agar kepesertaan aktif kembali, mohon Bapak/Ibu melunasi seluruh tunggakan paling lambat 10 Oktober 2026 melalui: Mobile JKN, bank/ATM/mobile banking, minimarket atau agen, atau datang langsung ke Kantor Cabang Salatiga dengan membawa KTP dan Kartu JKN (08.00 - 15.00 WIB).

Simpan bukti pembayaran. Apabila sudah membayar sebelum surat ini diterima, mohon abaikan surat ini. Informasi lebih lanjut: Care Center 165.

Salatiga, 22 September 2026
Kepala Bagian Kepesertaan
Budi Santosa, S.E.
"""

SURAT_PENIPUAN = """BPJS KESEHATAN - PEMBERITAHUAN PENTING

Yth. Bapak/Ibu Suminem,
Kartu BPJS Anda AKAN DIBLOKIR PERMANEN dalam 24 jam karena tunggakan iuran sebesar Rp1.500.000.
Agar kartu tidak diblokir, segera transfer ke rekening BCA 1234567890 a.n. Budi Santoso.
Setelah transfer, kirim bukti transfer dan KODE OTP yang masuk ke HP Anda ke WhatsApp 0812-0000-0000
atau klik tautan berikut untuk verifikasi: bit.ly/bpjs-verifikasi-cepat.
Jangan hubungi kantor BPJS karena proses ini hanya bisa lewat nomor di atas.
Terima kasih atas perhatian Anda.
Admin Pusat Verifikasi BPJS
"""

CONTOH = {
    "bpjs": {"teks": SURAT_BPJS, "label": "📄 Surat contoh: tunggakan BPJS (fiktif)"},
    "penipuan": {"teks": SURAT_PENIPUAN, "label": "⚠️ Surat contoh: pesan mencurigakan (fiktif)"},
}

TAMBAHAN_JSON = """

TAMBAHAN FORMAT
Tambahkan satu field lagi di JSON tingkat atas bernama "pengingat":
{"judul": "pengingat singkat dalam bahasa Indonesia, contoh: Bayar iuran BPJS", "tanggal": "YYYY-MM-DD"}
Isi "tanggal" dengan batas waktu terpenting yang TERTULIS di surat, dalam format YYYY-MM-DD.
Jika surat tidak menyebut batas waktu yang jelas, isi "pengingat" dengan null. Jangan menebak tanggal.
"""

# ---------- Tampilan ----------
st.markdown("""
<style>
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
  background: linear-gradient(180deg,#F5FAFF 0%,#DDECFF 45%,#BCD8FF 100%) !important;
  background-attachment: fixed !important;
}
[data-testid="stHeader"], [data-testid="stBottom"], [data-testid="stBottom"] > div,
[data-testid="stBottomBlockContainer"] { background: transparent !important; }

[data-testid="stSidebar"] { background: rgba(255,255,255,.35) !important; backdrop-filter: blur(14px); border-right: none !important; }
[data-testid="stSidebar"] > div:first-child { background: transparent !important; padding-top: .5rem; }

.block-container { max-width: 900px; padding-top: 2.5rem; }

.hero { text-align: center; margin: 1.5rem 0 1.2rem; }
.hero h1 { font-size: 2.4rem; font-weight: 800; margin: .6rem 0 .2rem; color: #10264D; }
.hero p { color: #5B6F92; margin: 0; }

.kartu { background: rgba(255,255,255,.9); border-radius: 18px; padding: 18px; box-shadow: 0 6px 20px rgba(47,111,234,.10); min-height: 205px; }
.kartu .ik { font-size: 1.5rem; }
.kartu b { display: block; margin: .4rem 0 .15rem; color: #10264D; }
.kartu span { color: #6C7FA3; font-size: .85rem; }

[data-testid="stChatInput"] { border-radius: 22px; background: #fff; box-shadow: 0 8px 26px rgba(47,111,234,.15); border: 1px solid rgba(47,111,234,.15); }
[data-testid="stChatMessage"] { background: rgba(255,255,255,.8); border-radius: 18px; }

.stButton > button, [data-testid="stDownloadButton"] button {
  border-radius: 999px; background: linear-gradient(135deg,#5B9BFF,#2F6FEA); color: #fff; border: none;
  padding: .5rem 1.2rem; box-shadow: 0 6px 16px rgba(47,111,234,.28);
}
.stButton > button:hover, [data-testid="stDownloadButton"] button:hover { background: linear-gradient(135deg,#4A8CF5,#2460DB); color: #fff; }
[data-testid="stSidebar"] .stButton > button { width: 100%; font-weight: 600; }
[data-testid="stSidebar"] [data-baseweb="select"] > div { border-radius: 14px; background: #fff; border: 1px solid rgba(47,111,234,.15); box-shadow: 0 2px 10px rgba(47,111,234,.08); }

.wa { display: inline-block; background: #25D366; color: #fff !important; padding: .55rem 1.2rem; border-radius: 999px;
      font-weight: 600; text-decoration: none; box-shadow: 0 6px 16px rgba(37,211,102,.30); }
.wa:hover { background: #1EBE5A; }

.brand { display: flex; align-items: center; gap: 12px; margin: .2rem 0 1.4rem; }
.brand .nama { font-weight: 800; font-size: 1.3rem; color: #10264D; line-height: 1.1; }
.brand .tim { font-size: .75rem; color: #7C8DAE; margin-top: 2px; }
.label { font-size: .7rem; letter-spacing: .09em; text-transform: uppercase; color: #7C8DAE; font-weight: 700; margin: 1rem 0 .35rem; }
.tips { background: rgba(255,255,255,.85); border-radius: 18px; padding: 14px 16px; box-shadow: 0 6px 18px rgba(47,111,234,.08); font-size: .85rem; color: #4D6086; margin-top: 1.4rem; }
.tips .judul { font-weight: 700; color: #10264D; margin-bottom: .4rem; }
.tips div { margin: .4rem 0; line-height: 1.35; }
.catatan { font-size: .75rem; color: #4D6086; background: rgba(79,141,247,.14); border-radius: 14px; padding: 10px 12px; margin-top: 1rem; line-height: 1.4; }
</style>
""", unsafe_allow_html=True)

if "api_msgs" not in st.session_state:
    st.session_state.api_msgs = []   # riwayat untuk model
if "tampil" not in st.session_state:
    st.session_state.tampil = []     # riwayat untuk layar

def ajukan(kunci):
    st.session_state.antri = kunci

with st.sidebar:
    st.markdown("""
<div class="brand">
<svg width="42" height="42" viewBox="0 0 100 100"><defs><linearGradient id="gi2" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#8EC5FF"/><stop offset="100%" stop-color="#2F6FEA"/></linearGradient></defs><rect x="6" y="6" width="88" height="88" rx="26" fill="url(#gi2)"/><rect x="24" y="31" width="52" height="38" rx="7" fill="#fff"/><path d="M27 37 L50 55 L73 37" fill="none" stroke="#2F6FEA" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/><circle cx="72" cy="68" r="13" fill="#fff"/><circle cx="72" cy="68" r="10" fill="#2F6FEA"/><path d="M67 68 L71 72 L78 64" fill="none" stroke="#fff" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
<div><div class="nama">NgertiBareng</div><div class="tim">oleh tim jujucimol</div></div>
</div>
""", unsafe_allow_html=True)

    st.markdown('<div class="label">Bahasa penjelasan</div>', unsafe_allow_html=True)
    pilihan = st.selectbox(
        "Bahasa penjelasan",
        ["Jawa", "Sunda", "Madura", "Bali", "Minang", "Inggris",
         "Indonesia sederhana", "Lainnya..."],
        label_visibility="collapsed",
    )
    if pilihan == "Lainnya...":
        bahasa = st.text_input("Tulis nama bahasanya").strip() or "Jawa"
    else:
        bahasa = pilihan

    st.markdown('<div class="label">Tampilan</div>', unsafe_allow_html=True)
    besar = st.toggle("🔍 Tulisan besar", value=False)

    st.write("")
    if st.button("＋ Percakapan baru"):
        st.session_state.api_msgs = []
        st.session_state.tampil = []
        st.rerun()

    st.markdown("""
<div class="tips">
<div class="judul">Cara pakai</div>
<div>📨 Kirim foto atau PDF surat lewat tombol <b>+</b> di kotak chat</div>
<div>📝 Baca ringkasan dan langkah yang harus dilakukan</div>
<div>💬 Tanya lanjutan seperti ngobrol biasa</div>
</div>
<div class="catatan">
Kualitas bahasa daerah masih dalam validasi. Mohon dicek penutur asli, dan jangan mengunggah data pribadi asli.
</div>
""", unsafe_allow_html=True)

if besar:
    st.markdown("""
<style>
[data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li { font-size: 1.35rem !important; line-height: 1.6 !important; }
[data-testid="stChatMessage"] [data-testid="stCaptionContainer"] p { font-size: 1.15rem !important; }
[data-testid="stChatMessage"] code { font-size: 1.2rem !important; }
[data-testid="stChatMessage"] h3 { font-size: 1.9rem !important; }
.hero p { font-size: 1.3rem !important; }
.kartu b { font-size: 1.2rem !important; }
.kartu span { font-size: 1.05rem !important; }
</style>
""", unsafe_allow_html=True)

# ---------- Fungsi bantu ----------
def blok_file(f):
    data = base64.b64encode(f.getvalue()).decode()
    if f.name.lower().endswith(".pdf"):
        return {"type": "document",
                "source": {"type": "base64", "media_type": "application/pdf", "data": data}}
    tipe = "image/png" if f.name.lower().endswith(".png") else "image/jpeg"
    return {"type": "image", "source": {"type": "base64", "media_type": tipe, "data": data}}

def ke_gemini(msgs):
    hasil = []
    for m in msgs:
        role = "user" if m["role"] == "user" else "model"
        parts = []
        if isinstance(m["content"], str):
            parts.append(types.Part.from_text(text=m["content"]))
        else:
            for b in m["content"]:
                if b["type"] == "text":
                    parts.append(types.Part.from_text(text=b["text"]))
                else:
                    src = b["source"]
                    parts.append(types.Part.from_bytes(
                        data=base64.b64decode(src["data"]),
                        mime_type=src["media_type"]))
        hasil.append(types.Content(role=role, parts=parts))
    return hasil

def bersihkan_json(mentah):
    mentah = mentah.strip()
    if mentah.startswith("```"):
        mentah = mentah.strip("`")
        if mentah.startswith("json"):
            mentah = mentah[4:]
    return mentah.strip()

def buat_ics(judul, tanggal_iso, catatan=""):
    d = datetime.strptime(tanggal_iso, "%Y-%m-%d")
    besok = d + timedelta(days=1)

    def esc(s):
        return (s.replace("\\", "\\\\").replace(";", "\\;")
                 .replace(",", "\\,").replace("\n", "\\n"))

    baris = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//NgertiBareng//ID", "CALSCALE:GREGORIAN",
        "BEGIN:VEVENT",
        f"UID:{uuid.uuid4()}@ngertibareng",
        f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        f"DTSTART;VALUE=DATE:{d.strftime('%Y%m%d')}",
        f"DTEND;VALUE=DATE:{besok.strftime('%Y%m%d')}",
        f"SUMMARY:{esc(judul)}",
        f"DESCRIPTION:{esc(catatan)}",
        "BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:Pengingat", "TRIGGER:-P3D", "END:VALARM",
        "BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:Pengingat", "TRIGGER:-P1D", "END:VALARM",
        "END:VEVENT", "END:VCALENDAR",
    ]
    return "\r\n".join(baris).encode("utf-8")

def tampilkan_hasil(h, idx=0):
    nama_bahasa = h.get("_bahasa", "Jawa")
    if h.get("peringatan_penipuan"):
        st.error(h["peringatan_penipuan"])
    st.info(f"Jenis surat: {h.get('jenis_surat', '-')}  |  Urgensi: {h.get('tingkat_urgensi', '-')}")
    kiri, kanan = st.columns(2)
    kiri.subheader(f"Bahasa {nama_bahasa}")
    kiri.write(h.get("ringkasan_jawa", ""))
    kanan.subheader("Bahasa Indonesia")
    kanan.write(h.get("ringkasan_indonesia", ""))

    st.subheader("Yang harus dilakukan")
    for l in h.get("checklist", []):
        st.markdown(f'**{l.get("langkah", "")}.** {l.get("jawa", "")}')
        st.caption(l.get("indonesia", ""))

    if h.get("hal_yang_perlu_dipastikan"):
        st.subheader("Perlu dipastikan")
        for x in h["hal_yang_perlu_dipastikan"]:
            st.write("- " + x)

    pesan = h.get("pesan_untuk_keluarga", "")
    st.subheader("Pesan untuk keluarga")
    st.code(pesan, language=None, wrap_lines=True)

    c1, c2 = st.columns(2)
    if pesan:
        url = "https://wa.me/?text=" + quote(pesan)
        c1.markdown(f'<a class="wa" href="{url}" target="_blank">💬 Kirim ke keluarga lewat WhatsApp</a>',
                    unsafe_allow_html=True)

    p = h.get("pengingat")
    if isinstance(p, dict) and p.get("tanggal"):
        try:
            data = buat_ics(p.get("judul") or h.get("jenis_surat", "Pengingat surat"),
                            p["tanggal"], h.get("jenis_surat", ""))
            c2.download_button("📅 Simpan pengingat ke kalender", data,
                               file_name="pengingat_ngertibareng.ics",
                               mime="text/calendar", key=f"ics_{idx}")
            st.caption(f"Pengingat untuk {p['tanggal']}. Buka file di HP, kalender akan mengingatkan "
                       "3 hari dan 1 hari sebelumnya. Mohon cek lagi tanggalnya dengan surat.")
        except ValueError:
            pass

# ---------- Sambutan ----------
sambutan = st.empty()
with sambutan.container():
    if not st.session_state.tampil:
        st.markdown("""
<div class="hero">
<svg width="84" height="84" viewBox="0 0 100 100"><defs><linearGradient id="gi" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#8EC5FF"/><stop offset="100%" stop-color="#2F6FEA"/></linearGradient></defs><rect x="6" y="6" width="88" height="88" rx="26" fill="url(#gi)"/><rect x="24" y="31" width="52" height="38" rx="7" fill="#fff"/><path d="M27 37 L50 55 L73 37" fill="none" stroke="#2F6FEA" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/><circle cx="72" cy="68" r="13" fill="#fff"/><circle cx="72" cy="68" r="10" fill="#2F6FEA"/><path d="M67 68 L71 72 L78 64" fill="none" stroke="#fff" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
<h1>Sugeng rawuh! 👋</h1>
<p>Kirim surat resmi, NgertiBareng bantu menjelaskannya dalam bahasa yang kamu mengerti.</p>
</div>
""", unsafe_allow_html=True)

        k1, k2, k3 = st.columns(3)
        k1.markdown('<div class="kartu"><div class="ik">📨</div><b>Kirim surat</b><span>Foto atau PDF lewat tombol + di kotak chat bawah.</span></div>', unsafe_allow_html=True)
        k2.markdown('<div class="kartu"><div class="ik">📝</div><b>Baca penjelasannya</b><span>Ringkasan, checklist tindakan, dan peringatan jika suratnya mencurigakan.</span></div>', unsafe_allow_html=True)
        k3.markdown('<div class="kartu"><div class="ik">💬</div><b>Tanya lanjutan</b><span>Ketik pertanyaan seperti ngobrol biasa, dalam bahasa pilihanmu.</span></div>', unsafe_allow_html=True)

        st.write("")
        st.caption("Belum punya surat? Coba contoh di bawah (data fiktif):")
        b1, b2 = st.columns(2)
        b1.button("📄 Coba dengan surat contoh", key="contoh_bpjs", on_click=ajukan, args=("bpjs",))
        b2.button("⚠️ Coba surat mencurigakan", key="contoh_penipuan", on_click=ajukan, args=("penipuan",))

        st.caption(
            "⚠️ NgertiBareng bukan pengganti petugas. Jawaban hanya berdasarkan isi surat. "
            "Mohon **jangan mengunggah data pribadi asli** pada versi percobaan ini, "
            "dan minta penutur asli mengecek kualitas bahasa daerah."
        )
    else:
        st.markdown("### NgertiBareng")

# ---------- Riwayat percakapan ----------
for i, m in enumerate(st.session_state.tampil):
    with st.chat_message(m["role"]):
        if m.get("files"):
            st.caption("📎 " + ", ".join(m["files"]))
        if m.get("hasil"):
            tampilkan_hasil(m["hasil"], i)
        elif m.get("text"):
            st.markdown(m["text"])

# ---------- Input ----------
antri = st.session_state.pop("antri", None)
masukan = st.chat_input(
    "Ketik pertanyaan, atau kirim surat (PDF/foto)...",
    accept_file=True,
    file_type=["pdf", "png", "jpg", "jpeg"],
)

if antri or masukan:
    if antri:
        teks = CONTOH[antri]["teks"]
        label = CONTOH[antri]["label"]
        files = []
    else:
        teks = (masukan.text or "").strip()
        label = teks
        files = masukan.files or []
    mode_surat = bool(antri) or bool(files) or len(teks) > 400

    if not st.session_state.tampil:
        sambutan.empty()

    isi = [blok_file(f) for f in files]
    if mode_surat:
        isi.append({"type": "text", "text": "SURAT:\n" + (teks or "(baca surat pada berkas di atas)")})
    else:
        isi.append({"type": "text", "text": teks})

    st.session_state.tampil.append(
        {"role": "user", "text": label, "files": [f.name for f in files]})
    with st.chat_message("user"):
        if files:
            st.caption("📎 " + ", ".join(f.name for f in files))
        if label:
            st.markdown(label)

    st.session_state.api_msgs.append({"role": "user", "content": isi})

    dasar = (SYSTEM_PROMPT + TAMBAHAN_JSON) if mode_surat else CHAT_PROMPT

    with st.chat_message("assistant"):
        with st.spinner("Sedang membaca..."):
            try:
                resp = client.models.generate_content(
                    model=MODEL,
                    contents=ke_gemini(st.session_state.api_msgs),
                    config=types.GenerateContentConfig(
                        system_instruction=prompt_dengan_bahasa(dasar, bahasa),
                        max_output_tokens=4000,
                    ),
                )
                jawaban = (resp.text or "").strip()
            except Exception as e:
                st.error(f"Gagal memanggil model: {e}")
                st.session_state.api_msgs.pop()
                st.session_state.tampil.pop()
                st.stop()

        hasil = None
        if mode_surat:
            try:
                hasil = json.loads(bersihkan_json(jawaban))
                hasil["_bahasa"] = bahasa
            except json.JSONDecodeError:
                hasil = None

        if hasil:
            tampilkan_hasil(hasil, len(st.session_state.tampil))
            st.session_state.tampil.append({"role": "assistant", "hasil": hasil})
        else:
            st.markdown(jawaban)
            st.session_state.tampil.append({"role": "assistant", "text": jawaban})

        st.session_state.api_msgs.append({"role": "assistant", "content": jawaban})