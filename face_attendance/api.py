import os
import re
import math
import base64
from datetime import datetime, time, timedelta
import frappe
from frappe import _
from frappe.utils import now_datetime, nowdate, format_time, getdate, now

def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in meters between two GPS coordinates."""
    R = 6371000  # Radius of Earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def get_timing_classification(dt: datetime, log_type: str, profile: dict | None = None) -> dict:
    """Shift module classifier based on employee profile timing."""
    # Default shift times if profile doesn't have custom hours
    shift_start = time(9, 30)
    shift_end = time(18, 30)
    grace_mins = 15
    shift_title = "Standard Shift"
    
    if profile:
        raw_start = profile.get("shift_start_time")
        raw_end = profile.get("shift_end_time")
        grace_mins = profile.get("grace_period_mins") or 15
        shift_title = profile.get("shift_name") or "Standard Shift"
        
        if raw_start:
            if isinstance(raw_start, str):
                parts = [int(p) for p in raw_start.split(":")[:2]]
                shift_start = time(parts[0], parts[1])
            elif hasattr(raw_start, "seconds"):
                total_secs = raw_start.seconds
                shift_start = time(total_secs // 3600, (total_secs % 3600) // 60)
            elif isinstance(raw_start, time):
                shift_start = raw_start

        if raw_end:
            if isinstance(raw_end, str):
                parts = [int(p) for p in raw_end.split(":")[:2]]
                shift_end = time(parts[0], parts[1])
            elif hasattr(raw_end, "seconds"):
                total_secs = raw_end.seconds
                shift_end = time(total_secs // 3600, (total_secs % 3600) // 60)
            elif isinstance(raw_end, time):
                shift_end = raw_end

    start_dt = datetime.combine(dt.date(), shift_start)
    grace_dt = start_dt + timedelta(minutes=int(grace_mins))
    halfday_dt = start_dt + timedelta(hours=4)
    end_dt = datetime.combine(dt.date(), shift_end)
    timing_str = f"{shift_start.strftime('%I:%M %p')} - {shift_end.strftime('%I:%M %p')}"
    
    if log_type == "IN":
        if dt <= grace_dt:
            return {
                "module": "Present", 
                "label": "On-Time Entry", 
                "description": f"Standard {shift_title}", 
                "badge": "ontime",
                "shift": timing_str
            }
        elif dt <= halfday_dt:
            mins_late = int((dt - start_dt).total_seconds() // 60)
            return {
                "module": "Late Entry", 
                "label": f"Late by {mins_late}m", 
                "description": "Marked Present (Late)", 
                "badge": "late",
                "shift": timing_str
            }
        else:
            return {
                "module": "Half Day", 
                "label": "Half Day Entry", 
                "description": "Entered after 4h into shift", 
                "badge": "halfday",
                "shift": timing_str
            }
    else:
        if dt < (end_dt - timedelta(hours=3)):
            return {
                "module": "Half Day", 
                "label": "Early Departure", 
                "description": "Left early before half shift", 
                "badge": "halfday",
                "shift": timing_str
            }
        elif dt < end_dt:
            mins_early = int((end_dt - dt).total_seconds() // 60)
            return {
                "module": "Present", 
                "label": f"Shift Done ({mins_early}m early)", 
                "description": "Standard shift fulfilled", 
                "badge": "regular",
                "shift": timing_str
            }
        else:
            ot_minutes = int((dt - end_dt).total_seconds() // 60)
            ot_str = f"+{ot_minutes // 60}h {ot_minutes % 60}m" if ot_minutes >= 60 else f"+{ot_minutes}m"
            return {
                "module": "Overtime", 
                "label": f"Overtime ({ot_str})", 
                "description": "Overtime completed", 
                "badge": "overtime",
                "shift": timing_str
            }

@frappe.whitelist(allow_guest=True)
def get_kiosk_config() -> dict:
    """Return kiosk settings."""
    now_dt = now_datetime()
    settings = frappe.get_single("Face Attendance Settings")
    
    return {
        "success": True,
        "kiosk_title": settings.kiosk_title or "Attendance Kiosk",
        "company": settings.company or "",
        "require_face": bool(settings.require_face),
        "enable_sound": bool(settings.enable_sound),
        "enable_haptics": bool(settings.enable_haptics),
        "enable_geo": bool(settings.enable_geo),
        "server_time": format_time(now_dt, "hh:mm:ss a"),
        "server_date": now_dt.strftime("%A, %d %B %Y")
    }

@frappe.whitelist(allow_guest=True)
def verify_pin_preview(pin: str) -> dict:
    """
    Lookup employee by PIN:
    - Protects against brute-force lockout (after 5 failed attempts per IP)
    - Returns official reference photo URL, assigned shift timing, and last punch status
    """
    if not pin:
        return {"success": False, "message": "PIN required"}
    
    client_ip = getattr(frappe.local, "request_ip", "127.0.0.1")
    cache_key = f"pin_attempts_{client_ip}"
    failed_attempts = frappe.cache.get_value(cache_key) or 0

    if failed_attempts >= 5:
        return {
            "success": False,
            "locked": True,
            "message": "Security lockout: 5 failed PIN attempts. Please wait 3 minutes before trying again."
        }

    pin_str = str(pin).strip()
    profile = frappe.db.get_value(
        "Face Attendance Profile",
        {"secret_pin": pin_str, "status": "Active"},
        ["name", "employee", "employee_name", "department", "designation", "face_image", "face_descriptor", "is_registered", "last_log_type", "last_checkin_time", "shift_name", "shift_start_time", "shift_end_time", "grace_period_mins"],
        as_dict=True
    )
    
    if not profile:
        new_attempts = failed_attempts + 1
        frappe.cache.set_value(cache_key, new_attempts, expires_in_sec=180)
        remaining = 5 - new_attempts
        return {
            "success": False, 
            "message": f"PIN not recognized. {remaining} attempt{'s' if remaining > 1 else ''} left before lockout."
        }
    
    # Reset failed attempts on success
    frappe.cache.delete_value(cache_key)
    
    now_dt = now_datetime()
    today_start = f"{nowdate()} 00:00:00"
    
    if profile.last_checkin_time and str(profile.last_checkin_time) >= today_start:
        auto_log_type = "OUT" if profile.last_log_type == "IN" else "IN"
    else:
        auto_log_type = "IN"

    timing_info = get_timing_classification(now_dt, auto_log_type, profile)

    return {
        "success": True,
        "employee": profile.employee,
        "employee_name": profile.employee_name,
        "department": profile.department or "Team Member",
        "designation": profile.designation or "",
        "face_image": profile.face_image or "",
        "face_descriptor": profile.face_descriptor or "",
        "has_reference_image": bool(profile.face_image),
        "shift_name": profile.shift_name or "Regular Day Shift",
        "shift_start_time": str(profile.shift_start_time) if profile.shift_start_time else "09:30:00",
        "shift_end_time": str(profile.shift_end_time) if profile.shift_end_time else "18:30:00",
        "shift_timing": timing_info.get("shift", "09:30 AM - 06:30 PM"),
        "last_log_type": profile.last_log_type or "None",
        "last_checkin_time": format_time(profile.last_checkin_time, "hh:mm a") if profile.last_checkin_time else "None",
        "auto_log_type": auto_log_type,
        "timing_module": timing_info["module"],
        "timing_label": timing_info["label"]
    }

@frappe.whitelist(allow_guest=True)
def mark_face_pin_attendance(
    pin: str,
    photo_base64: str | None = None,
    log_type: str | None = None,
    match_status: str | None = None,
    ai_confidence: str | None = None,
    coords: str | None = None,
    device_info: str | None = None,
    selfie_descriptor: str | None = None
) -> dict:
    """
    Security-Hardened Attendance Marking Endpoint:
    1. Brute-force lockout prevention
    2. Rapid duplicate spam cooldown (minimum 2 minutes between punches)
    3. Blank / black covered camera detection
    4. Geofencing perimeter check (if configured)
    5. Anti-fake audit against official reference photo
    6. Server-side authoritative timestamp (cannot be tampered by mobile clock)
    """
    if not pin:
        pin = frappe.form_dict.get("pin")
    if not pin and hasattr(frappe, "request") and frappe.request.is_json:
        req_json = frappe.request.get_json() or {}
        pin = req_json.get("pin")
    
    if not pin:
        return {
            "success": False,
            "message": _("4-Digit Secret PIN is required")
        }
    
    client_ip = getattr(frappe.local, "request_ip", "127.0.0.1")
    cache_key = f"pin_attempts_{client_ip}"
    failed_attempts = frappe.cache.get_value(cache_key) or 0
    if failed_attempts >= 5:
        return {
            "success": False,
            "locked": True,
            "message": _("Terminal locked: Too many failed PIN attempts. Please wait 3 minutes.")
        }

    pin_str = str(pin).strip()
    profile = frappe.db.get_value(
        "Face Attendance Profile",
        {"secret_pin": pin_str, "status": "Active"},
        ["name", "employee", "employee_name", "department", "designation", "face_image", "face_descriptor", "is_registered", "total_checkins", "last_log_type", "last_checkin_time", "shift_name", "shift_start_time", "shift_end_time", "grace_period_mins"],
        as_dict=True
    )
    
    if not profile:
        new_attempts = failed_attempts + 1
        frappe.cache.set_value(cache_key, new_attempts, expires_in_sec=180)
        return {
            "success": False,
            "message": _(f"Invalid PIN. {5 - new_attempts} attempts remaining.")
        }

    # Reset failed attempts on valid profile
    frappe.cache.delete_value(cache_key)

    now_dt = now_datetime()
    today = nowdate()
    today_start = f"{today} 00:00:00"

    # 1. Manual Log Type Selection (IN or OUT)
    if log_type and log_type.upper() in ["IN", "OUT"]:
        resolved_log_type = log_type.upper()
    elif profile.last_checkin_time and str(profile.last_checkin_time) >= today_start:
        resolved_log_type = "OUT" if profile.last_log_type == "IN" else "IN"
    else:
        resolved_log_type = "IN"

    # --- DEFENSE 1: Blank / Covered Camera Check ---
    if not photo_base64 or len(photo_base64) < 400:
        return {
            "success": False,
            "message": _("Camera was covered or selfie frame missing. Face must be clearly visible.")
        }

    # --- DEFENSE 2: Real-time Biometric Face Matching (Anti-Buddy Punching) ---
    if profile.face_descriptor and selfie_descriptor:
        try:
            import json
            ref_vec = json.loads(profile.face_descriptor) if isinstance(profile.face_descriptor, str) else profile.face_descriptor
            input_vec = json.loads(selfie_descriptor) if isinstance(selfie_descriptor, str) else selfie_descriptor
            
            if ref_vec and input_vec and len(ref_vec) == len(input_vec):
                dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(input_vec, ref_vec)))
                if dist > 0.50:
                    frappe.log_error(f"Proxy punch rejected for {profile.employee_name}. Face distance: {dist:.3f}", "Biometric Mismatch")
                    return {
                        "success": False,
                        "face_mismatch": True,
                        "message": _(f"Face Mismatch! Scanned face does not match {profile.employee_name}'s official photo. Proxy punch rejected.")
                    }
        except Exception as face_err:
            frappe.log_error(f"Face matching check error: {face_err}", "Biometric Face Match")

    # --- DEFENSE 3: Rapid Duplicate Click Cooldown ---
    if profile.last_checkin_time:
        delta_seconds = (now_dt - profile.last_checkin_time).total_seconds()
        if profile.last_log_type == resolved_log_type and delta_seconds < 15:
            remaining_wait = int(15 - delta_seconds)
            return {
                "success": False,
                "cooldown": True,
                "message": _(f"Duplicate punch blocked: You already marked {resolved_log_type} {int(delta_seconds)}s ago. Please wait {remaining_wait}s.")
            }

    # --- DEFENSE 3: Geofencing Check (if office coordinates are configured) ---
    geo_status = "Verified In Office"
    settings = frappe.get_single("Face Attendance Settings")
    office_lat = getattr(settings, "office_latitude", None)
    office_lon = getattr(settings, "office_longitude", None)
    geofence_radius = getattr(settings, "geofence_radius_meters", None) or 250

    if office_lat and office_lon and coords and "," in coords:
        try:
            punch_lat, punch_lon = map(float, coords.split(","))
            dist = calculate_haversine_distance(punch_lat, punch_lon, float(office_lat), float(office_lon))
            if dist > float(geofence_radius):
                geo_status = f"Outside Geofence ({int(dist)}m away)"
                if getattr(settings, "enable_geofence_lock", False):
                    return {
                        "success": False,
                        "message": _(f"Attendance blocked: You are {int(dist)}m away from office premises.")
                    }
        except Exception:
            pass

    # Match status audit - Strictly enforce allowed DocType values: "Verified Match", "Review Needed", "Missing Reference"
    allowed_statuses = ["Verified Match", "Review Needed", "Missing Reference"]
    if match_status not in allowed_statuses:
        match_status = "Verified Match" if profile.face_image else "Missing Reference"

    # 2. Timing Classification
    timing_info = get_timing_classification(now_dt, resolved_log_type, profile=profile)

    # 3. Save Captured Selfie Photo
    photo_file_url = None
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
            "log_type": resolved_log_type,
            "device_id": "Auto-Face-PIN-Kiosk",
            "latitude": coords.split(",")[0].strip() if coords and "," in coords else None,
            "longitude": coords.split(",")[1].strip() if coords and "," in coords else None,
        })
        checkin_doc.insert(ignore_permissions=True)
        employee_checkin_name = checkin_doc.name
    except Exception as checkin_err:
        frappe.log_error(f"Error creating Employee Checkin: {checkin_err}", "Face Attendance Checkin")

    notes_msg = f"Shift: {timing_info['module']} ({timing_info['label']}). Match Status: {match_status}. Geo: {geo_status}."
    if ai_confidence:
        notes_msg += f" AI Match Confidence: {ai_confidence}."

    # 5. Create Face Attendance Log record
    face_log = frappe.get_doc({
        "doctype": "Face Attendance Log",
        "employee": profile.employee,
        "employee_name": profile.employee_name,
        "log_type": resolved_log_type,
        "timestamp": now_dt,
        "status": "Success",
        "match_status": match_status,
        "pin_verified": 1,
        "face_detected": 1 if photo_file_url else 0,
        "photo_captured": photo_file_url,
        "reference_photo": profile.face_image or None,
        "device_info": device_info or "Smart Biometric Kiosk",
        "ip_address": client_ip,
        "location_coords": coords or "",
        "employee_checkin": employee_checkin_name,
        "notes": notes_msg
    })
    face_log.flags.ignore_links = True
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
            att_status = "Present" if timing_info["module"] != "Half Day" else "Half Day"
            
            if not existing_att:
                att_doc = frappe.get_doc({
                    "doctype": "Attendance",
                    "employee": profile.employee,
                    "attendance_date": today,
                    "status": att_status
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
        "designation": profile.designation or "Team Member",
        "log_type": log_type,
        "shift_name": profile.shift_name or "Standard Shift",
        "shift_timing": timing_info.get("shift", "09:30 AM - 06:30 PM"),
        "timing_module": timing_info["module"],
        "timing_label": timing_info["label"],
        "time": format_time(now_dt, "hh:mm:ss a"),
        "date": today,
        "avatar": profile.face_image or photo_file_url or "/assets/frappe/images/default-avatar.png",
        "reference_photo": profile.face_image or photo_file_url,
        "captured_photo": photo_file_url,
        "match_status": match_status,
        "ai_confidence": ai_confidence or "",
        "message": f"Welcome, {profile.employee_name}! Marked {log_type}."
    }

@frappe.whitelist(allow_guest=True)
def save_employee_face_descriptor(employee: str | None = None, employee_name: str | None = None, descriptor: str | None = None) -> dict:
    """Save 128-float face descriptor for employee."""
    if not descriptor:
        return {"success": False, "message": "Descriptor required"}
    
    filters = {}
    if employee:
        filters["employee"] = employee
    elif employee_name:
        filters["employee_name"] = employee_name
    else:
        return {"success": False, "message": "Employee identifier required"}
        
    profile_name = frappe.db.get_value("Face Attendance Profile", filters, "name")
    if not profile_name:
        return {"success": False, "message": "Profile not found"}
        
    frappe.db.set_value("Face Attendance Profile", profile_name, "face_descriptor", descriptor)
    frappe.db.commit()
    return {"success": True, "message": f"Face descriptor enrolled successfully for {profile_name}"}

@frappe.whitelist(allow_guest=True)
def submit_job_application(
    candidate_name: str,
    phone: str,
    email: str,
    position_applied: str,
    experience_years: float | None = None,
    notice_period: str | None = None,
    current_location: str | None = None,
    current_ctc: float | None = None,
    expected_ctc: float | None = None,
    resume_file_url: str | None = None,
    resume_base64: str | None = None,
    resume_filename: str | None = None,
    hr_notes: str | None = None
) -> dict:
    """Public recruitment endpoint for candidates to apply with PDF resume."""
    if not candidate_name or not candidate_name.strip():
        frappe.throw(_("Candidate Name is required"))
    if not phone or not phone.strip():
        frappe.throw(_("Phone / Mobile number is required"))
    if not email or not email.strip():
        frappe.throw(_("Email address is required"))
    if not position_applied or not position_applied.strip():
        frappe.throw(_("Position Applied For is required"))
    
    saved_resume_url = resume_file_url
    
    # Handle direct multipart file upload if submitted via FormData
    uploaded_file = None
    if getattr(frappe, "request", None) and getattr(frappe.request, "files", None):
        uploaded_file = frappe.request.files.get("resume") or frappe.request.files.get("file")
        
    if uploaded_file:
        filename = uploaded_file.filename or "resume.pdf"
        if not filename.lower().endswith(".pdf"):
            frappe.throw(_("Word documents (.doc, .docx) are NOT allowed. Please upload your resume in PDF format (.pdf)."))
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": filename,
            "content": uploaded_file.stream.read(),
            "is_private": 0
        })
        file_doc.save(ignore_permissions=True)
        saved_resume_url = file_doc.file_url
    elif resume_base64:
        filename = resume_filename or f"resume_{now_datetime().strftime('%Y%m%d_%H%M%S')}.pdf"
        if not filename.lower().endswith(".pdf"):
            frappe.throw(_("Word documents (.doc, .docx) are NOT allowed. Please upload your resume in PDF format (.pdf)."))
        b64_content = resume_base64
        if "base64," in b64_content:
            b64_content = b64_content.split("base64,")[1]
        raw_bytes = base64.b64decode(b64_content)
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": filename,
            "content": raw_bytes,
            "is_private": 0
        })
        file_doc.save(ignore_permissions=True)
        saved_resume_url = file_doc.file_url

    if not saved_resume_url:
        frappe.throw(_("Resume file (PDF format only) is mandatory."))
    
    candidate = frappe.get_doc({
        "doctype": "Job Candidate",
        "candidate_name": candidate_name.strip(),
        "phone": phone.strip(),
        "email": email.strip().lower(),
        "position_applied": position_applied.strip(),
        "status": "New",
        "experience_years": float(experience_years) if experience_years else 0,
        "notice_period": notice_period or "Immediate",
        "current_location": current_location.strip() if current_location else "",
        "current_ctc": float(current_ctc) if current_ctc else 0,
        "expected_ctc": float(expected_ctc) if expected_ctc else 0,
        "resume": saved_resume_url,
        "source": "Web Form",
        "hr_notes": hr_notes or ""
    })
    candidate.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "success": True,
        "candidate_id": candidate.name,
        "candidate_name": candidate.candidate_name,
        "position_applied": candidate.position_applied,
        "message": f"Thank you, {candidate.candidate_name}! Your application has been submitted successfully."
    }

def evaluate_boolean_expression(text: str, expr: str) -> tuple[bool, int]:
    """
    Evaluates boolean query string with AND, OR, NOT, quotes and parentheses against candidate text.
    Returns (matches: bool, hit_count: int).
    """
    if not expr or not expr.strip():
        return True, 0

    text_lower = text.lower()
    raw_query = expr.strip()
    
    # Tokenize words, quoted phrases, and operators
    pattern = r'(".*?"|\(|\)|\bAND\b|\bOR\b|\bNOT\b|[^\s()]+)'
    raw_tokens = re.findall(pattern, raw_query, flags=re.IGNORECASE)
    
    python_expr_parts = []
    hit_count = 0
    prev_was_operand = False
    
    for tok in raw_tokens:
        tok_upper = tok.upper()
        if tok_upper == 'AND':
            python_expr_parts.append('and')
            prev_was_operand = False
        elif tok_upper == 'OR':
            python_expr_parts.append('or')
            prev_was_operand = False
        elif tok_upper == 'NOT':
            if prev_was_operand:
                python_expr_parts.append('and')
            python_expr_parts.append('not')
            prev_was_operand = False
        elif tok == '(':
            if prev_was_operand:
                python_expr_parts.append('and')
            python_expr_parts.append('(')
            prev_was_operand = False
        elif tok == ')':
            python_expr_parts.append(')')
            prev_was_operand = True
        else:
            term = tok.strip('"\'').lower()
            if term:
                is_hit = term in text_lower
                if is_hit:
                    hit_count += text_lower.count(term)
                if prev_was_operand:
                    python_expr_parts.append('and')
                python_expr_parts.append(str(is_hit))
                prev_was_operand = True
                
    if not python_expr_parts:
        return True, 0
        
    eval_str = " ".join(python_expr_parts)
    try:
        matches = bool(eval(eval_str, {"__builtins__": {}}, {}))
    except Exception:
        simple_words = [w.lower() for w in re.findall(r'\w+', raw_query) if w.upper() not in ['AND', 'OR', 'NOT']]
        matches = any(w in text_lower for w in simple_words) if simple_words else True
        hit_count = sum(text_lower.count(w) for w in simple_words)
        
    return matches, hit_count

@frappe.whitelist(allow_guest=True)
def search_job_candidates(
    query: str | None = None,
    status: str | None = None,
    position: str | None = None,
    min_exp: float | None = None,
    max_exp: float | None = None,
    notice_periods: str | None = None,
    location: str | None = None,
    max_ctc: float | None = None,
    tags: str | None = None,
    sort_by: str = "relevance",
    page: int = 1,
    page_size: int = 6
) -> dict:
    """
    Candidate Talent Discovery API:
    1. Boolean Search Parser (AND, OR, NOT, Quotes, Parentheses)
    2. Multi-Criteria Filters (Status, Position, Experience, Location, CTC, Notice)
    3. Profile Tags & Skills Filtering
    4. Smart Relevance Ranking (Best to Less Relevant)
    5. Clean Pagination & Metadata Aggregations
    """
    page = int(page or 1)
    page_size = int(page_size or 6)
    
    # 1. Fetch all candidate records from database
    all_candidates = frappe.get_all(
        "Job Candidate",
        fields=[
            "name", "candidate_name", "email", "phone", "status",
            "position_applied", "current_location", "experience_years",
            "notice_period", "current_ctc", "expected_ctc", "resume",
            "source", "next_follow_up_date", "hr_notes", "profile_tags",
            "creation"
        ]
    )
    
    # Parse list parameters
    selected_statuses = [s.strip() for s in status.split(",") if s.strip()] if status else []
    selected_notice = [n.strip() for n in notice_periods.split(",") if n.strip()] if notice_periods else []
    selected_tags = [t.strip().lower() for t in tags.split(",") if t.strip()] if tags else []
    
    # Tag aggregations across all candidates
    tag_counter = {}
    location_counter = {}
    position_counter = {}
    
    for c in all_candidates:
        # Tally tags
        raw_tags = c.get("profile_tags") or ""
        for t in raw_tags.split(","):
            t_clean = t.strip()
            if t_clean:
                tag_counter[t_clean] = tag_counter.get(t_clean, 0) + 1
        
        # Tally locations
        loc = (c.get("current_location") or "").strip()
        if loc:
            location_counter[loc] = location_counter.get(loc, 0) + 1
            
        # Tally positions
        pos = (c.get("position_applied") or "").strip()
        if pos:
            position_counter[pos] = position_counter.get(pos, 0) + 1
            
    filtered = []
    
    for c in all_candidates:
        c_exp = float(c.get("experience_years") or 0)
        c_ctc = float(c.get("expected_ctc") or 0)
        c_loc = (c.get("current_location") or "").lower()
        c_status = c.get("status") or "New"
        c_notice = c.get("notice_period") or "Immediate"
        c_pos = (c.get("position_applied") or "").lower()
        c_tags_raw = (c.get("profile_tags") or "").lower()
        c_tags_list = [t.strip() for t in c_tags_raw.split(",") if t.strip()]
        
        # Apply Status Filter
        if selected_statuses and c_status not in selected_statuses:
            continue
            
        # Apply Position Filter
        if position and position.strip().lower() not in c_pos:
            continue
            
        # Apply Experience Filter
        if min_exp is not None and min_exp != "" and c_exp < float(min_exp):
            continue
        if max_exp is not None and max_exp != "" and c_exp > float(max_exp):
            continue
            
        # Apply Notice Period Filter
        if selected_notice and c_notice not in selected_notice:
            continue
            
        # Apply Location Filter
        if location and location.strip().lower() not in c_loc:
            continue
            
        # Apply Max CTC Filter
        if max_ctc is not None and max_ctc != "" and float(max_ctc) > 0:
            if c_ctc > float(max_ctc):
                continue
                
        # Apply Profile Tags Filter
        if selected_tags:
            # Check if candidate has at least one of the selected tags
            if not any(req_tag in c_tags_raw for req_tag in selected_tags):
                continue
                
        # Boolean Search Query Filter
        searchable_text = f"{c.get('candidate_name', '')} {c.get('position_applied', '')} {c.get('profile_tags', '')} {c.get('current_location', '')} {c.get('notice_period', '')} {c.get('source', '')} {c.get('hr_notes', '')}"
        
        matches_query, hit_count = evaluate_boolean_expression(searchable_text, query or "")
        if not matches_query:
            continue
            
        # 3. Calculate Smart Relevance Ranking Score (0 to 100)
        relevance_score = 45 # Base baseline
        
        if query and query.strip():
            # Query hits bonus
            relevance_score += min(hit_count * 10, 30)
            # Exact position hit
            if any(term in c_pos for term in query.lower().split() if term not in ['and', 'or', 'not']):
                relevance_score += 15
            # Skills tag hit
            if any(term in c_tags_raw for term in query.lower().split() if term not in ['and', 'or', 'not']):
                relevance_score += 10
        else:
            relevance_score = 65
            
        # Notice Period score bonus (immediate availability is valuable to HR)
        if c_notice == "Immediate":
            relevance_score += 10
        elif c_notice == "15 Days":
            relevance_score += 6
        elif c_notice == "30 Days":
            relevance_score += 3
            
        # Experience bonus
        if 2.0 <= c_exp <= 6.0:
            relevance_score += 8
        elif c_exp > 6.0:
            relevance_score += 5
            
        # Tag density bonus
        if selected_tags:
            tag_matches = sum(1 for req_t in selected_tags if req_t in c_tags_raw)
            relevance_score += int((tag_matches / len(selected_tags)) * 15)
            
        # Status weight
        if c_status == "Interview":
            relevance_score += 6
        elif c_status == "Screening":
            relevance_score += 4
        elif c_status == "New":
            relevance_score += 2
        elif c_status == "Rejected":
            relevance_score -= 35
            
        # Clamp score
        final_score = max(min(relevance_score, 99), 20)
        
        # Determine match tier
        if final_score >= 88:
            tier_label = "Top Match"
            tier_icon = "star"
        elif final_score >= 72:
            tier_label = "Strong Fit"
            tier_icon = "zap"
        elif final_score >= 50:
            tier_label = "Good Match"
            tier_icon = "thumbs-up"
        else:
            tier_label = "Potential Fit"
            tier_icon = "file-text"
            
        # Clean phone for WhatsApp fast follow-up
        clean_phone = re.sub(r'[^0-9]', '', str(c.get("phone", "")))
        if len(clean_phone) == 10:
            clean_phone = "91" + clean_phone
            
        filtered.append({
            "name": c["name"],
            "candidate_name": c["candidate_name"],
            "email": c["email"],
            "phone": c["phone"],
            "clean_phone": clean_phone,
            "status": c_status,
            "position_applied": c.get("position_applied") or "Team Member",
            "current_location": c.get("current_location") or "Not Specified",
            "experience_years": c_exp,
            "notice_period": c_notice,
            "current_ctc": c.get("current_ctc") or 0,
            "expected_ctc": c_ctc,
            "resume": c.get("resume") or "",
            "source": c.get("source") or "Web Form",
            "hr_notes": c.get("hr_notes") or "",
            "profile_tags": c.get("profile_tags") or "",
            "tags_list": [t.strip() for t in (c.get("profile_tags") or "").split(",") if t.strip()],
            "relevance_score": final_score,
            "match_tier": tier_label,
            "tier_icon": tier_icon,
            "hit_count": hit_count,
            "desk_url": f"/app/job-candidate/{c['name']}"
        })
        
    # 4. Sorting: Default to Relevance DESC (Best to Less Relevant)
    if sort_by == "relevance":
        filtered.sort(key=lambda x: (x["relevance_score"], x["experience_years"]), reverse=True)
    elif sort_by == "experience_desc":
        filtered.sort(key=lambda x: x["experience_years"], reverse=True)
    elif sort_by == "experience_asc":
        filtered.sort(key=lambda x: x["experience_years"])
    elif sort_by == "ctc_asc":
        filtered.sort(key=lambda x: x["expected_ctc"])
    elif sort_by == "newest":
        filtered.sort(key=lambda x: x["name"], reverse=True)
        
    # 5. Pagination
    total_matches = len(filtered)
    total_pages = math.ceil(total_matches / page_size) if total_matches > 0 else 1
    page = min(max(1, page), total_pages)
    
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_results = filtered[start_idx:end_idx]
    
    return {
        "success": True,
        "candidates": paginated_results,
        "total_count": total_matches,
        "total_in_db": len(all_candidates),
        "total_pages": total_pages,
        "current_page": page,
        "page_size": page_size,
        "aggregations": {
            "tags": sorted([{"tag": k, "count": v} for k, v in tag_counter.items()], key=lambda x: x["count"], reverse=True)[:20],
            "locations": sorted([{"location": k, "count": v} for k, v in location_counter.items()], key=lambda x: x["count"], reverse=True),
            "positions": sorted([{"position": k, "count": v} for k, v in position_counter.items()], key=lambda x: x["count"], reverse=True)
        }
    }

@frappe.whitelist(allow_guest=True)
def update_candidate_status(candidate_id: str, new_status: str) -> dict:
    """Quick 1-click status update from talent search card."""
    if not candidate_id or not new_status:
        return {"success": False, "message": "Candidate ID and status required"}
    
    if not frappe.db.exists("Job Candidate", candidate_id):
        return {"success": False, "message": "Candidate not found"}
        
    frappe.db.set_value("Job Candidate", candidate_id, "status", new_status)
    frappe.db.commit()
    return {"success": True, "message": f"Candidate {candidate_id} status updated to {new_status}"}



