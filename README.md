# Employee Status & Overtime Manager

[![Frappe Framework](https://img.shields.io/badge/Frappe-v15%20%7C%20v16%20%7C%20v17-blue.svg)](https://frappeframework.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](license.txt)
[![Version](https://img.shields.io/badge/version-0.0.1-purple.svg)](pyproject.toml)

An enterprise-ready **Employee Status, Overtime & Half-Day Management App** for **Frappe Framework** and **ERPNext**. Provides real-time attendance status visibility, overtime calculation, session-based half-day leave tracking, and an interactive executive command dashboard.

---

## 🌟 Key Features

### 1. ⏱️ Overtime Management (`Employee Overtime Request`)
- **Automated Duration Calculation**: Calculates exact overtime hours from start and end times (including overnight shifts).
- **Customizable Overtime Types**: Regular Overtime, Weekend Overtime, Holiday Overtime, and Emergency Support.
- **Pay Computation**: Optional automated overtime pay calculation (`hourly_rate * overtime_hours`).
- **Approval Workflow**: Integrated `Draft` ➔ `Pending Approval` ➔ `Approved` / `Rejected` states with reason auditing.
- **Auto Status Sync**: Automatically updates the employee's daily status upon approval.

### 2. 🌓 Half-Day Leave Tracking (`Employee Half Day Request`)
- **Session-Based Logging**: Choose between **First Half (Morning)** or **Second Half (Afternoon)**.
- **Leave Type Mapping**: Links with Casual Leave, Sick Leave, Privilege Leave, Compensatory Off, or Unpaid Leave.
- **Emergency Contact**: Tracks contact info during absence for operational continuity.
- **Instant Approvals**: Managerial approval/rejection with notification alerts.

### 3. 📋 Live Status Roster (`Employee Daily Status`)
- Real-time snapshot of daily attendance status:
  - 🟢 **Present**
  - ⏱️ **Overtime Active**
  - 🌓 **Half Day (First Half / Second Half)**
  - 🏖️ **On Leave** / **Work From Home**
- Fast search by employee name, department, or status badge.

### 4. 🚀 Interactive UI/UX Command Center Dashboard
- **Live KPI Metric Cards**:
  - Total Active Employees
  - Present Today
  - Overtime Hours Logged Today
  - Half-Day Leaves Today
  - Pending Approvals Counter
- **Quick Modals**: "+ Quick Overtime Entry" and "+ Quick Half Day Request" dialogs.
- **1-Click Approvals**: Instant approve/reject action buttons directly from the dashboard table.
- **Interactive Date Navigation**: Check past or future scheduled statuses with a built-in date picker.

---

## 🏗️ Architecture & DocTypes

```
employee_status_manager/
├── employee_status_manager/
│   ├── api.py                          # Whitelisted backend APIs for stats & roster
│   ├── hooks.py                        # App hooks, desk icons & permissions
│   ├── doctype/
│   │   ├── employee_overtime_request/  # Overtime DocType & workflow controller
│   │   ├── employee_half_day_request/  # Half-Day DocType & session logic
│   │   └── employee_daily_status/      # Daily snapshot roster model
│   ├── page/
│   │   └── employee_status_dashboard/  # Custom UI/UX Command Center
│   └── workspace/
│       └── employee_status_manager/    # Desk Workspace & Shortcuts
```

---

## 📦 Installation

To install this app on your Frappe bench:

```bash
# 1. Fetch the app from GitHub (replace with your repo URL)
bench get-app https://github.com/rudrasinh11/employee_status_manager

# 2. Install the app on your site
bench --site <your-site-name> install-app employee_status_manager

# 3. Migrate and build assets
bench --site <your-site-name> migrate
bench build --app employee_status_manager
```

---

## 💻 Usage

1. Open your Frappe Desk (`/app`).
2. Navigate to **Employee Status & Overtime Hub** via the Desk launcher or `/app/employee_status_dashboard`.
3. Use **New Overtime Request** or **New Half Day Request** to submit employee entries.
4. Managers can review and approve or reject submissions in 1 click!

---

## 📄 License

This project is licensed under the [MIT License](license.txt).
Author: **rudrasinh11** (<rudrasinh3115@gmail.com>)
