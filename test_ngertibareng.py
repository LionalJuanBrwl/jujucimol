"""
Tes otomatis NgertiBareng (jalur IBM Langflow + smoke test Streamlit).

Jalankan dari folder jujucimol (venv aktif, Langflow hidup):
    python -m pytest test_ngertibareng.py -v

Kunci dibaca dari .env. Jangan menulis kunci di file ini.
Jawaban disimpan di folder hasil_tes/ untuk dicek manual.
"""
import json
import os
import re
import time
import uuid
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

load_dotenv()

LANGFLOW_URL = os.getenv("LANGFLOW_URL", "http://127.0.0.1:7860").rstrip("/")
FLOW_ID = os.getenv("LANGFLOW_FLOW_ID")
API_KEY = os.getenv("LANGFLOW_API_KEY")
TIMEOUT = 120
OUT_DIR = Path("hasil_tes")
OUT_DIR.mkdir(exist_ok=True)

SURAT_BPJS = """BADAN PENYELENGGARA JAMINAN SOSIAL KESEHATAN
Kantor Cabang Salatiga
Nomor   : 123/KC-SLT/IX/2026
Tanggal : 1 Oktober 2026
Perihal : Pemberitahuan Tunggakan Iuran JKN-KIS

Yth. Ibu Sumiyati, Nomor Peserta: 0001234567890

Iuran JKN-KIS Kelas 3 atas nama Ibu belum dibayarkan selama 3 (tiga) bulan,
yaitu Juli, Agustus, dan September 2026. Status kepesertaan Ibu saat ini tidak aktif.

Tunggakan per bulan : Rp 42.000
Total tunggakan     : Rp 126.000
Batas pelunasan     : 31 Oktober 2026

Mohon melunasi melalui bank, kantor pos, minimarket, atau aplikasi Mobile JKN.
Jika kesulitan, datang ke Kantor Cabang membawa KTP, Kartu JKN-KIS, dan bukti
pembayaran, atau hubungi 165.
"""

ALLOWED_RUPIAH = {"42.000", "126.000"}
JAVA_WORDS = [
    "sampun", "kedah", "kedhah", "mboten", "boten", "panjenengan", "sing",
    "saking", "dados", "menawi", "mangga", "badhe", "kudu", "iku", "ing ",
    "nggih", "mbah", "ibu", "bapak", "kula",
]


# ---------- helper ----------
def _extract_text(data: dict) -> str:
    try:
        out = data["outputs"][0]["outputs"][0]
        res = out.get("results", {}).get("message", {})
        if isinstance(res, dict) and res.get("text"):
            return res["text"]
        msg = out.get("outputs", {}).get("message", {}).get("message")
        if msg:
            return msg if isinstance(msg, str) else str(msg)
        if out.get("messages"):
            return out["messages"][0].get("message", "")
    except (KeyError, IndexError, TypeError):
        pass
    return ""


JEDA = float(os.getenv("JEDA_TES", "4"))


def kuota_habis(status, teks):
    t = (teks or "").lower()
    return status == 500 and ("429" in t or "quota" in t or "too many requests" in t)


def skip_jika_kuota(status, teks):
    if kuota_habis(status, teks):
        pytest.skip("Kuota Gemini habis (429). Coba lagi nanti.")


def ask(text, session_id=None, retries=2):
    url = f"{LANGFLOW_URL}/api/v1/run/{FLOW_ID}?stream=false"
    payload = {
        "input_value": text,
        "input_type": "chat",
        "output_type": "chat",
        "session_id": session_id or str(uuid.uuid4()),
    }
    headers = {"Content-Type": "application/json", "x-api-key": API_KEY}
    last = (0, "")
    time.sleep(JEDA)
    for i in range(retries + 1):
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT)
            last = (r.status_code, _extract_text(r.json()) if r.ok else r.text[:300])
            if r.ok and last[1]:
                return last
            if kuota_habis(*last):
                return last  # jangan mengulang, hanya menghabiskan kuota
        except requests.RequestException as e:
            last = (0, f"{type(e).__name__}")
        time.sleep(2 * (i + 1))
    return last


def save(name, text):
    (OUT_DIR / f"{name}.txt").write_text(text, encoding="utf-8")


def parse_json(teks):
    """Ubah jawaban Langflow jadi objek Python. None jika bukan JSON."""
    bersih = re.sub(r"^```(?:json)?|```$", "", teks.strip(), flags=re.M).strip()
    try:
        return json.loads(bersih)
    except json.JSONDecodeError:
        return None


def ratakan(obj, prefix=""):
    """Ratakan JSON jadi daftar (nama_kunci_kecil, nilai)."""
    hasil = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            nama = f"{prefix}.{k}".lower()
            hasil.append((nama, v))
            hasil += ratakan(v, nama)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hasil += ratakan(v, f"{prefix}[{i}]")
    return hasil


# ---------- fixtures ----------
@pytest.fixture(scope="session", autouse=True)
def langflow_siap():
    if not (FLOW_ID and API_KEY):
        pytest.skip("LANGFLOW_FLOW_ID / LANGFLOW_API_KEY belum ada di .env")
    try:
        requests.get(f"{LANGFLOW_URL}/health", timeout=5)
    except requests.RequestException:
        pytest.skip(f"Langflow tidak terjangkau di {LANGFLOW_URL}. Jalankan dulu.")


@pytest.fixture(scope="session")
def jawaban_bpjs():
    sid = str(uuid.uuid4())
    status, teks = ask(SURAT_BPJS, session_id=sid)
    skip_jika_kuota(status, teks)
    save("jawaban_bpjs", teks)
    return {"status": status, "teks": teks, "session": sid}


# ---------- tes jalur teks / Langflow ----------
def test_langflow_merespons(jawaban_bpjs):
    assert jawaban_bpjs["status"] == 200
    assert len(jawaban_bpjs["teks"]) > 100, "Jawaban kosong atau terlalu pendek"


def test_jawaban_berupa_json_valid(jawaban_bpjs):
    data = parse_json(jawaban_bpjs["teks"])
    assert isinstance(data, dict), "Jawaban bukan JSON yang valid"


def test_fakta_penting_benar(jawaban_bpjs):
    t = jawaban_bpjs["teks"].lower()
    assert "126.000" in t or "126000" in t, "Total tunggakan tidak muncul"
    assert "31 oktober" in t or "31 okt" in t or "2026-10-31" in t, "Batas waktu tidak muncul"


def test_dokumen_yang_dibawa_disebut(jawaban_bpjs):
    t = jawaban_bpjs["teks"].lower()
    assert "ktp" in t, "KTP tidak disebut"
    assert "jkn" in t or "kartu" in t, "Kartu JKN-KIS tidak disebut"


def test_tidak_ada_angka_rupiah_karangan(jawaban_bpjs):
    ditemukan = set(re.findall(r"Rp\s?([\d.]+\d)", jawaban_bpjs["teks"]))
    asing = ditemukan - ALLOWED_RUPIAH
    assert not asing, f"Angka Rupiah tidak ada di surat: {asing}"


def test_ada_bahasa_jawa(jawaban_bpjs):
    t = jawaban_bpjs["teks"].lower()
    cocok = [w for w in JAVA_WORDS if w in t]
    assert len(cocok) >= 3, f"Kata Jawa kurang terdeteksi: {cocok}"


def test_ada_terjemahan_indonesia(jawaban_bpjs):
    teks = jawaban_bpjs["teks"]
    data = parse_json(teks)
    if data is None:  # flow kembali ke teks biasa
        t = teks.lower()
        assert any(p in t for p in ["artinya", "bahasa indonesia", "terjemahan"]), \
            "Terjemahan Indonesia tidak ditemukan"
        return
    pasangan = ratakan(data)
    cocok = [
        k for k, v in pasangan
        if any(x in k for x in ["indonesia", "terjemahan", "arti", "translation"])
        and isinstance(v, str) and len(v) > 20
    ]
    assert cocok, f"Tidak ada field terjemahan. Kunci JSON: {[k for k, _ in pasangan][:25]}"


def test_ada_langkah_tindakan(jawaban_bpjs):
    data = parse_json(jawaban_bpjs["teks"])
    assert data is not None, "Jawaban bukan JSON"
    pasangan = ratakan(data)
    daftar = [
        v for k, v in pasangan
        if isinstance(v, list) and any(x in k for x in ["langkah", "tindakan", "checklist", "action", "step"])
    ]
    if not daftar:  # cadangan: daftar apa pun yang berisi >= 3 item
        daftar = [v for _, v in pasangan if isinstance(v, list) and len(v) >= 3]
    assert daftar, f"Tidak ada daftar langkah. Kunci JSON: {[k for k, _ in pasangan][:25]}"
    assert max(len(x) for x in daftar) >= 3, "Kurang dari 3 langkah"


def test_kunci_api_tidak_bocor(jawaban_bpjs):
    t = jawaban_bpjs["teks"]
    for pola in [r"sk-ant-", r"AIza[0-9A-Za-z_-]{10,}", r"sk-[A-Za-z0-9_-]{20,}"]:
        assert not re.search(pola, t), "Ada pola kunci API di jawaban!"


def test_tanya_lanjutan_nyambung(jawaban_bpjs):
    status, teks = ask("Kalau saya tidak punya KTP bagaimana?", session_id=jawaban_bpjs["session"])
    skip_jika_kuota(status, teks)
    save("tanya_lanjutan_ktp", teks)
    assert status == 200 and len(teks) > 50
    assert "ktp" in teks.lower()


def test_input_kosong_tidak_crash():
    status, teks = ask("   ", retries=0)
    skip_jika_kuota(status, teks)
    save("input_kosong", f"status={status}\n{teks}")
    assert status != 500, "Server error saat input kosong"


def test_teks_bukan_surat_tidak_mengarang():
    status, teks = ask("Resep nasi goreng apa?", retries=0)
    skip_jika_kuota(status, teks)
    save("bukan_surat", teks)
    assert status == 200
    assert "126.000" not in teks, "Jawaban memakai angka dari surat lain"


# ---------- smoke test Streamlit ----------
def test_streamlit_app_terbuka_tanpa_error():
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    if not Path("app.py").exists():
        pytest.skip("Jalankan pytest dari folder jujucimol (app.py tidak ditemukan)")
    at = AppTest.from_file("app.py", default_timeout=60).run()
    assert not at.exception, f"App error saat dimuat: {at.exception}"