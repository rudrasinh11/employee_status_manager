import os
import re
import base64
import frappe
from frappe import _
from frappe.utils import now_datetime, nowdate, format_time, getdate

@frappe.whitelist(allow_guest=True)
def get_kiosk_config() -> dict:
    """Return kiosk settings and basic status."""
    try:
        settings = frappe.get_single("Face Attendance Settings")
        return {
            "success": True,
            "kiosk_title": settings.kiosk_title or "Smart Face & PIN Attendance",
            "company": settings.company or "",
            "auto_reset_seconds": settings.auto_reset_seconds or 3,
            "default_log_type": settings.default_log_type or "Auto Detect",
            "require_face": bool(settings.require_face),
            "enable_sound": bool(settings.enable_sound),
            "enable_haptics": bool(settings.enable_haptics),
            "enable_geo": bool(settings.enable_geo),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "kiosk_title": "Smart Face & PIN Attendance",
            "auto_reset_seconds": 3,
            "default_log_type": "Auto Detect",
            "require_face": True,
            "enable_sound": True,
            "enable_haptics": True,
            "enable_geo": True
        }

@frappe.whitelist(allow_guest=True)
def verify_pin_preview(pin: str) -> dict:
    """Quick lookup to show employee name & avatar when 4 digits are entered."""
    if not pin:
        return {"success": False, "message": "PIN required"}
    
    pin_str = str(pin).strip()
    profile = frappe.db.get_value(
        "Face Attendance Profile",
        {"secret_pin": pin_str, "status": "Active"},
        ["name", "employee", "employee_name", "department", "designation", "face_image", "last_log_type"],
        as_dict=True
    )
    
    if not profile:
        return {"success": False, "message": "PIN not recognized"}
    
    # Predict next action: if last was IN -> OUT, else IN
    next_log = "OUT" if profile.last_log_type == "IN" else "IN"
    
    return {
        "success": True,
        "employee": profile.employee,
        "employee_name": profile.employee_name,
        "department": profile.department or "",
        "designation": profile.designation or "",
        "face_image": profile.face_image or "",
        "suggested_log_type": next_log
    }

@frappe.whitelist(allow_guest=True)
def mark_face_pin_attendance(
    pin: str,
    photo_base64: str | None = None,
    log_type: str | None = None,
    coords: str | None = None,
    device_info: str | None = None
) -> dict:
    """
    Main attendance marking endpoint:
    - Verifies 4-digit PIN against Face Attendance Profile
    - Saves the live selfie image as a Frappe File
    - Creates Face Attendance Log
    - Creates standard Employee Checkin
    - Marks/updates Attendance in HRMS
    - Updates Face Attendance Profile stats
    """
    if not pin:
        frappe.throw(_("4-Digit Secret PIN is required"))
    
    pin_str = str(pin).strip()
    
    # 1. Lookup Profile
    profile = frappe.db.get_value(
        "Face Attendance Profile",
        {"secret_pin": pin_str, "status": "Active"},
        ["name", "employee", "employee_name", "department", "designation", "face_image", "total_checkins", "last_log_type"],
        as_dict=True
    )
    
    if not profile:
        frappe.response["http_status_code"] = 400
        return {
            "success": False,
            "message": _("Invalid 4-digit PIN. Please try again or ask HR to enroll your PIN.")
        }
    
    # 2. Determine Log Type
    if not log_type or log_type == "Auto Detect":
        log_type = "OUT" if profile.last_log_type == "IN" else "IN"
    elif log_type not in ["IN", "OUT"]:
        log_type = "IN"
        
    now_dt = now_datetime()
    today = nowdate()
    
    # 3. Save Captured Selfie Photo if provided
    photo_file_url = None
    if photo_base64 and len(photo_base64) > 100:
        try:
            if "," in photo_base64:
                header, encoded = photo_base64.split(",", 1)
            else:
                encoded = photo_base64
            
            image_data = base64.b64decode(encoded)
            file_name = f"attendance_snap_{profile.employee}_{now_dt.strftime('%Y%m%d_%H%M%S')}.jpg"
            
            saved_file = frappe.get_doc({
                "doctype": "File",
                "file_name": file_name,
                "content": image_data,
                "is_private": 0
            })
            saved_file.insert(ignore_permissions=True)
            photo_file_url = saved_file.file_url
        except Exception as file_err:
            frappe.log_error(f"Error saving attendance selfie: {file_err}", "Face Attendance Photo Save")

    # 4. Create Standard Employee Checkin
    employee_checkin_name = None
    try:
        checkin_doc = frappe.get_doc({
            "doctype": "Employee Checkin",
            "employee": profile.employee,
            "time": now_dt,
            "log_type": log_type,
            "device_id": "Face-PIN-Kiosk",
            "latitude": coords.split(",")[0].strip() if coords and "," in coords else None,
            "longitude": coords.split(",")[1].strip() if coords and "," in coords else None,
        })
        checkin_doc.insert(ignore_permissions=True)
        employee_checkin_name = checkin_doc.name
    except Exception as checkin_err:
        frappe.log_error(f"Error creating Employee Checkin: {checkin_err}", "Face Attendance Checkin")

    # 5. Create Face Attendance Log record
    face_log = frappe.get_doc({
        "doctype": "Face Attendance Log",
        "employee": profile.employee,
        "employee_name": profile.employee_name,
        "log_type": log_type,
        "timestamp": now_dt,
        "status": "Success",
        "pin_verified": 1,
        "face_detected": 1 if photo_file_url else 0,
        "photo_captured": photo_file_url,
        "device_info": device_info or (getattr(frappe.local, "request", None) and frappe.local.request.headers.get("User-Agent", "Unknown Device")[:140]) or "Mobile Device",
        "ip_address": getattr(frappe.local, "request_ip", "127.0.0.1"),
        "location_coords": coords or "",
        "employee_checkin": employee_checkin_name,
        "notes": f"Verified via 4-Digit PIN. Photo {'Captured' if photo_file_url else 'Skipped'}."
    })
    face_log.insert(ignore_permissions=True)

    # 6. Mark Attendance in HRMS / Attendance DocType
    try:
        if frappe.db.exists("DocType", "Attendance"):
            existing_att = frappe.db.get_value(
                "Attendance",
                {"employee": profile.employee, "attendance_date": today, "docstatus": ["!=", 2]},
                ["name", "status"],
                as_dict=True
            )
            if not existing_att:
                att_doc = frappe.get_doc({
                    "doctype": "Attendance",
                    "employee": profile.employee,
                    "attendance_date": today,
                    "status": "Present"
                })
                att_doc.insert(ignore_permissions=True)
                att_doc.submit()
    except Exception as att_err:
        frappe.log_error(f"Error auto-marking Attendance: {att_err}", "Face Attendance Direct Mark")

    # 7. Update Face Attendance Profile stats
    frappe.db.set_value(
        "Face Attendance Profile",
        profile.name,
        {
            "last_checkin_time": now_dt,
            "last_log_type": log_type,
            "total_checkins": (profile.total_checkins or 0) + 1
        },
        update_modified=False
    )
    frappe.db.commit()

    return {
        "success": True,
        "employee_id": profile.employee,
        "employee_name": profile.employee_name,
        "department": profile.department or "General",
        "designation": profile.designation or "Employee",
        "log_type": log_type,
        "time": format_time(now_dt, "hh:mm:ss a"),
        "date": today,
        "avatar": profile.face_image or photo_file_url or "/assets/frappe/images/default-avatar.png",
        "captured_photo": photo_file_url,
        "total_checkins": (profile.total_checkins or 0) + 1,
        "message": f"Welcome, {profile.employee_name}! Attendance marked as {log_type}."
    }

@frappe.whitelist(allow_guest=True)
def enroll_employee_face(
    employee: str,
    pin: str,
    photo_base64: str | None = None,
    admin_pin: str | None = None
) -> dict:
    """Enroll or update an employee's 4-digit PIN and reference selfie photo."""
    settings = frappe.get_single("Face Attendance Settings")
    configured_admin_pin = settings.kiosk_admin_pin or "1234"
    
    if frappe.session.user == "Guest":
        if not admin_pin or str(admin_pin).strip() != str(configured_admin_pin).strip():
            frappe.response["http_status_code"] = 403
            return {"success": False, "message": "Invalid Admin PIN. Access denied."}

    if not employee:
        frappe.throw(_("Employee ID is required"))
    
    pin_str = str(pin).strip()
    if not pin_str.isdigit() or len(pin_str) != 4:
        frappe.throw(_("PIN must be exactly 4 digits"))
        
    existing_pin = frappe.db.get_value(
        "Face Attendance Profile",
        {"secret_pin": pin_str, "employee": ["!=", employee], "status": "Active"},
        "employee"
    )
    if existing_pin:
        frappe.throw(_(f"This PIN is already assigned to employee {existing_pin}. Please choose a unique 4-digit PIN."))

    face_image_url = None
    if photo_base64 and len(photo_base64) > 100:
        try:
            if "," in photo_base64:
                header, encoded = photo_base64.split(",", 1)
            else:
                encoded = photo_base64
            image_data = base64.b64decode(encoded)
            file_name = f"profile_face_{employee}_{now_datetime().strftime('%Y%m%d_%H%M%S')}.jpg"
            
            saved_file = frappe.get_doc({
                "doctype": "File",
                "file_name": file_name,
                "content": image_data,
                "is_private": 0
            })
            saved_file.insert(ignore_permissions=True)
            face_image_url = saved_file.file_url
        except Exception as e:
            frappe.log_error(f"Error saving reference face: {e}", "Face Attendance Enrollment")

    profile_name = frappe.db.get_value("Face Attendance Profile", {"employee": employee}, "name")
    
    if profile_name:
        profile_doc = frappe.get_doc("Face Attendance Profile", profile_name)
        profile_doc.secret_pin = pin_str
        profile_doc.status = "Active"
        if face_image_url:
            profile_doc.face_image = face_image_url
            profile_doc.is_registered = 1
        profile_doc.save(ignore_permissions=True)
    else:
        profile_doc = frappe.get_doc({
            "doctype": "Face Attendance Profile",
            "employee": employee,
            "secret_pin": pin_str,
            "status": "Active",
            "is_registered": 1 if face_image_url else 0,
            "face_image": face_image_url or ""
        })
        profile_doc.insert(ignore_permissions=True)

    if face_image_url and frappe.db.exists("Employee", employee):
        cur_emp_image = frappe.db.get_value("Employee", employee, "image")
        if not cur_emp_image:
            frappe.db.set_value("Employee", employee, "image", face_image_url, update_modified=False)

    frappe.db.commit()

    return {
        "success": True,
        "message": f"Successfully enrolled {profile_doc.employee_name} ({employee}) with PIN {pin_str}!",
        "face_image": face_image_url or profile_doc.face_image
    }

@frappe.whitelist(allow_guest=True)
def get_today_kiosk_feed(limit: int = 15) -> dict:
    """Get recent check-ins for the live ticker / activity feed."""
    today = nowdate()
    logs = frappe.get_all(
        "Face Attendance Log",
        filters={"status": "Success"},
        fields=["name", "employee", "employee_name", "log_type", "timestamp", "photo_captured"],
        order_by="timestamp desc",
        limit=int(limit)
    )
    
    for l in logs:
        l["time_formatted"] = format_time(l["timestamp"], "hh:mm a")
        if not l.get("photo_captured"):
            l["photo_captured"] = frappe.db.get_value("Face Attendance Profile", {"employee": l["employee"]}, "face_image") or "/assets/frappe/images/default-avatar.png"
            
    return {"success": True, "feed": logs}

@frappe.whitelist(allow_guest=True)
def get_employees_list(admin_pin: str | None = None) -> dict:
    """Return active employees with enrollment status for registration UI."""
    settings = frappe.get_single("Face Attendance Settings")
    configured_admin_pin = settings.kiosk_admin_pin or "1234"
    
    if frappe.session.user == "Guest":
        if not admin_pin or str(admin_pin).strip() != str(configured_admin_pin).strip():
            frappe.response["http_status_code"] = 403
            return {"success": False, "message": "Invalid Admin PIN"}

    employees = frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["name", "employee_name", "department", "designation", "image"],
        order_by="employee_name asc"
    )
    
    profiles = {p.employee: p for p in frappe.get_all(
        "Face Attendance Profile",
        fields=["employee", "secret_pin", "face_image", "is_registered", "status"]
    )}
    
    result = []
    for emp in employees:
        prof = profiles.get(emp.name)
        result.append({
            "employee": emp.name,
            "employee_name": emp.employee_name,
            "department": emp.department or "",
            "designation": emp.designation or "",
            "avatar": (prof.face_image if prof and prof.face_image else emp.image) or "",
            "is_enrolled": bool(prof and prof.secret_pin),
            "masked_pin": "••••" if (prof and prof.secret_pin) else "Not Set",
            "pin": prof.secret_pin if prof else ""
        })
        
    return {"success": True, "employees": result}
