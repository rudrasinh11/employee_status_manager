# 📸 Face Attendance for Frappe Framework & HRMS

[![Frappe Framework](https://img.shields.io/badge/Frappe-v15%20%7C%20v16%20%7C%20v17-blue.svg)](https://frappeframework.com/)
[![Vue.js 3](https://img.shields.io/badge/Vue.js-3.x-42b883.svg)](https://vuejs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](license.txt)
[![Status: Production Ready](https://img.shields.io/badge/Status-Production%20Ready-emerald.svg)](#)

A modern, high-speed **Face Recognition & 4-Digit Secret PIN Attendance System** built for the **Frappe Framework**, **ERPNext**, and **HRMS**.

Designed specifically for **mobile phone cameras** and **shared tablet kiosks**, employees can step up, align their face with the live camera viewfinder, enter their 4-digit secret PIN, and get their attendance marked in milliseconds with photo verification.

---

## 🌟 Key Highlights

- **📱 Mobile-First & Kiosk Ready**: Works natively in any mobile browser (Chrome, Safari, Firefox, Edge) using HTML5 `navigator.mediaDevices.getUserMedia`.
- **🤳 Live Biometric Framing & Auto-Snap**: High-tech HUD oval reticle with animated laser scan beam and instant camera shutter flash upon capture.
- **🔢 4-Digit Secret PIN Security**: Combines PIN knowledge with live face capture for two-factor verification.
- **⚡ Auto-Confirm & Instant Reset**:
  - Automatically identifies the employee on the 4th digit.
  - Takes a live high-resolution selfie snapshot.
  - Celebrates with confetti and employee details badge.
  - Auto-resets in 3 seconds ready for the next person in line.
- **🔊 Zero-Dependency Web Audio Synthesis**: Tactile keypad clicks, camera shutter sound, celebration victory chime, and error feedback generated directly in the browser via Web Audio API oscillators.
- **🏢 Deep ERPNext / HRMS Integration**:
  - Automatically creates standard **Employee Checkin** records (`IN` / `OUT`).
  - Seamlessly marks/updates the HRMS **Attendance** register.
  - Saves the captured live selfie snapshot directly into Frappe's file manager (`File` DocType).
- **📍 Geolocation Audit**: Optional GPS coordinate recording with each check-in.
- **🛠️ Self-Service Face & PIN Enrollment**: HR managers can register employee PINs and take reference selfies directly from the kiosk interface with an Admin PIN.
- **📊 Desk Workspace**: Comes with a pre-configured Frappe Desk workspace (`/app/face-attendance`) for managers to review audit trails, inspect captured photos, and tweak settings.

---

## 🏗️ Architecture & Tech Stack

```
[ Mobile Phone / Tablet Kiosk ]
        │  (Vue.js 3 SPA + Web Audio + HTML5 Camera)
        ▼
   POST /api/method/face_attendance.api.mark_face_pin_attendance
        │
        ├── 1. PIN & Profile Validation (Face Attendance Profile)
        ├── 2. Save Live Camera Snapshot (Frappe File Manager)
        ├── 3. Create Audit Record (Face Attendance Log)
        ├── 4. Record Checkin (Employee Checkin - HRMS)
        └── 5. Mark Daily Status (Attendance DocType - Present)
```

- **Backend**: Frappe Framework (Python 3.10 - 3.14)
- **Frontend**: Vue.js 3, Modern Glassmorphism CSS, Web Audio API, HTML5 Canvas & MediaDevices
- **Database**: MariaDB / PostgreSQL

---

## 🚀 Installation & Setup

### 1. Fetch & Install the App

Run in your bench directory:

```bash
cd ~/frappe-bench

# Fetch the repository from GitHub
bench get-app https://github.com/rudrasinh11/face_attendance.git

# Install app on your site
bench --site <your-site-name> install-app face_attendance

# Migrate database schema
bench --site <your-site-name> migrate
```

### 2. Launch the Kiosk Web App

Start your bench development server (or access via production Nginx):

```bash
bench start
```

Access the application in any browser:
- **Local Kiosk**: `http://localhost:8000/face-attendance`
- **On Mobile Devices (same Wi-Fi)**: `http://<your-computer-ip>:8000/face-attendance`

---

## 📱 How to Use

### For Employees:
1. Open `http://<your-host>:8000/face-attendance` on your smartphone or walk up to the wall-mounted office tablet.
2. Select **CHECK IN** or **CHECK OUT** (or leave it on Auto Detect).
3. Align your face inside the glowing oval reticle.
4. Punch your **4-Digit Secret PIN** on the numeric touch keypad.
5. *Snap!* The camera captures your selfie snapshot, validates your PIN, and marks your attendance with a celebration confirmation screen!

### For HR / Admins:
1. Click the **⚙️ Settings icon** in the top-right corner.
2. Enter the Kiosk Admin PIN (Default: `1234`, configurable in *Face Attendance Settings*).
3. Select an active employee, enter a 4-digit PIN for them, click **📸 SNAP CAMERA PHOTO**, and hit **SAVE & ENROLL**.

---

## 📦 DocTypes Included

| DocType | Type | Description |
| :--- | :--- | :--- |
| **Face Attendance Settings** | Single | Configure kiosk title, auto-reset timer, default log mode, sound & geo toggles, and admin PIN. |
| **Face Attendance Profile** | Master | Maps each employee to their secret 4-digit PIN, reference selfie photo, and check-in stats. |
| **Face Attendance Log** | Transaction | Complete audit trail of every punch with timestamp, captured live selfie photo, IN/OUT type, and IP/GPS. |

---

## 🔌 API Endpoints

### 1. `face_attendance.api.get_kiosk_config`
Returns public kiosk configuration (title, auto-reset time, audio toggles, default mode).

### 2. `face_attendance.api.verify_pin_preview`
- **Params**: `pin` (string)
- **Returns**: Employee name, department, profile avatar, and suggested next punch type (`IN` / `OUT`).

### 3. `face_attendance.api.mark_face_pin_attendance`
- **Params**: `pin`, `photo_base64`, `log_type`, `coords`, `device_info`
- **Returns**: Success status, employee details, timestamp, and saved photo URL.

### 4. `face_attendance.api.enroll_employee_face`
- **Params**: `employee`, `pin`, `photo_base64`, `admin_pin`
- **Returns**: Enrollment confirmation.

### 5. `face_attendance.api.get_today_kiosk_feed`
- **Returns**: Real-time list of today's check-ins with photo thumbnails.

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

## 📄 License

[MIT](license.txt) © 2026 rudrasinh11
