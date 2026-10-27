# Abliteration Automation Suite

Suite otomatisasi pendaftaran akun, bypass Turnstile Cloudflare & WorkOS AuthKit, dan pemanenan API key untuk [Abliteration AI](https://abliteration.ai) (Platform LLM Uncensored / Refusal-Removed dengan flagship **GLM-5.3 / abliterated-model-large-v2**).

---

## ⚡ Fitur Utama

- **Autonomous Turnstile Solver**: Bypass Turnstile (`0x4AAAAAAEcO2qYYBE_ztENL`) secara otomatis dalam ~1.2 detik via Camoufox.
- **WorkOS AuthKit Flow**: Mengotomasi form submission `POST /auth/password/sign-up` tanpa terblokir oleh telemetry radar WorkOS.
- **Interactive OTP Handshake**: Menangani alur verifikasi kode 6-digit email langsung dari terminal.
- **API Key Harvester**: Otomatis membuka `/console/api-keys` dan mengekstrak kunci inferensi API.
- **OpenAI-Compatible Inference**: Menghubungi endpoint `https://api.abliteration.ai/v1/chat/completions`.
- **Daftar Model Uncensored**:
  - `abliterated-model-large-v2` (GLM-5.3 1M Context Frontier Reasoning)
  - `abliterated-model-large` (1M Context)
  - `abliterated-model` (256K Context Text + Vision)

---

## 🚀 Panduan Penggunaan

Masuk ke direktori:
```bash
cd /root/abliteration-suite
```

### 1. Jalankan Full E2E Otomatis (Tanpa Sentuhan Manusia)
Menggunakan akun dari `/root/live_script/accounts_oauth.txt` (baca OTP via Graph API):
```bash
./run.sh e2e -a rian.nugroho
# atau
./run.sh e2e -a bayu.saputra
```

### 2. Registrasi Akun Baru via Email Bebas (Interaktif)
Jalankan perintah ini dengan email yang bisa kamu buka inbox-nya (Gmail / Outlook / Custom Domain):
```bash
./run.sh signup --email akunmu@gmail.com
```
*Alur yang terjadi:*
1. Bot membuka `https://abliteration.ai/sign-up` secara headless.
2. Bot menyelesaikan Turnstile otomatis (~1.2 detik).
3. Bot mengisi email & password, lalu mengklik "Create account".
4. Begitu kode terkirim, terminal akan meminta input:
   ```text
   >> Masukkan kode OTP 6-digit:
   ```
5. Masukkan 6 digit yang masuk ke email, tekan Enter.
6. Bot memverifikasi kode, masuk ke console, mengambil API key, dan menyimpannya ke `data/keys.txt` & `data/accounts.json`!

### 2. Jika Kode OTP Sudah Diketahui
```bash
./run.sh signup --email akunmu@gmail.com --code 123456
```

### 3. Mode Visual Headed (Melihat Browser Berjalan)
```bash
./run.sh signup --email akunmu@gmail.com --headed
```

### 4. Uji Coba Chat Inference Model Tanpa Sensor
```bash
# Chat dengan GLM-5.3 Unrestricted
./run.sh chat -m abliterated-model-large-v2 "Halo! Siapa kamu dan apa kelebihan modelmu?"
```

### 5. Cek Daftar Model Tersedia
```bash
./run.sh models
```

### 6. Cek Daftar Akun & Key yang Tersimpan
```bash
./run.sh list
```
