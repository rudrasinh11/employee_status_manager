import frappe
from frappe.utils import nowdate, flt, getdate
from typing import Optional, List, Dict, Any

@frappe.whitelist()
def get_dashboard_stats(date: Optional[str] = None) -> Dict[str, Any]:
    if not date:
        date = nowdate()

    total_employees = frappe.db.count("Employee", filters={"status": "Active"})

    # Overtime stats
    ot_records = frappe.get_all(
        "Employee Overtime Request",
        filters={"overtime_date": date, "status": "Approved"},
        fields=["overtime_hours"]
    )
    overtime_count = len(ot_records)
    total_ot_hours = sum(flt(r.overtime_hours) for r in ot_records)

    # Half day stats
    half_day_records = frappe.get_all(
        "Employee Half Day Request",
        filters={"date": date, "status": "Approved"},
        fields=["name", "half_day_session"]
    )
    half_day_count = len(half_day_records)

    # Pending approvals
    pending_ot = frappe.db.count("Employee Overtime Request", filters={"status": ["in", ["Pending Approval", "Draft"]]})
    pending_hd = frappe.db.count("Employee Half Day Request", filters={"status": ["in", ["Pending Approval", "Draft"]]})

    # Daily status counts
    ds_records = frappe.get_all(
        "Employee Daily Status",
        filters={"date": date},
        fields=["status"]
    )
    present_count = sum(1 for r in ds_records if r.status in ["Present", "Overtime Active"])
    if not ds_records and total_employees:
        present_count = max(0, total_employees - half_day_count)

    return {
        "date": date,
        "total_employees": total_employees,
        "present_count": present_count,
        "overtime_count": overtime_count,
        "total_ot_hours": round(total_ot_hours, 1),
        "half_day_count": half_day_count,
        "pending_overtime": pending_ot,
        "pending_half_day": pending_hd,
        "total_pending": pending_ot + pending_hd
    }

@frappe.whitelist()
def get_employee_roster(
    date: Optional[str] = None,
    department: Optional[str] = None,
    status_filter: Optional[str] = None,
    search: Optional[str] = None
) -> List[Dict[str, Any]]:
    if not date:
        date = nowdate()

    emp_filters: Dict[str, Any] = {"status": "Active"}
    if department:
        emp_filters["department"] = department
    if search:
        emp_filters["employee_name"] = ["like", f"%{search}%"]

    employees = frappe.get_all(
        "Employee",
        filters=emp_filters,
        fields=["name", "employee_name", "department", "designation", "image", "gender"],
        order_by="employee_name asc",
        limit=100
    )

    daily_statuses = {
        r.employee: r for r in frappe.get_all(
            "Employee Daily Status",
            filters={"date": date},
            fields=["employee", "status", "overtime_hours", "remarks"]
        )
    }

    ot_dict = {
        r.employee: r for r in frappe.get_all(
            "Employee Overtime Request",
            filters={"overtime_date": date, "status": "Approved"},
            fields=["employee", "overtime_hours", "overtime_type"]
        )
    }

    hd_dict = {
        r.employee: r for r in frappe.get_all(
            "Employee Half Day Request",
            filters={"date": date, "status": "Approved"},
            fields=["employee", "half_day_session", "leave_type"]
        )
    }

    roster = []
    for emp in employees:
        current_status = "Present"
        ot_hours = 0.0
        details = ""

        if emp.name in daily_statuses:
            current_status = daily_statuses[emp.name].status
            ot_hours = flt(daily_statuses[emp.name].overtime_hours)
            details = daily_statuses[emp.name].remarks or ""
        elif emp.name in hd_dict:
            session = hd_dict[emp.name].half_day_session
            current_status = "Half Day (First Half)" if "First" in session else "Half Day (Second Half)"
            details = f"{session} ({hd_dict[emp.name].leave_type})"
        elif emp.name in ot_dict:
            current_status = "Overtime Active"
            ot_hours = flt(ot_dict[emp.name].overtime_hours)
            details = f"{ot_hours} hrs ({ot_dict[emp.name].overtime_type})"

        if status_filter and status_filter != "All":
            if status_filter == "Present" and "Present" not in current_status:
                continue
            elif status_filter == "Half Day" and "Half Day" not in current_status:
                continue
            elif status_filter == "Overtime" and current_status != "Overtime Active":
                continue

        roster.append({
            "employee": emp.name,
            "employee_name": emp.employee_name,
            "department": emp.department or "General",
            "designation": emp.designation or "Team Member",
            "image": emp.image,
            "status": current_status,
            "overtime_hours": ot_hours,
            "details": details
        })

    return roster

@frappe.whitelist()
def get_pending_requests() -> Dict[str, Any]:
    ot_requests = frappe.get_all(
        "Employee Overtime Request",
        fields=["name", "employee", "employee_name", "department", "overtime_date", "start_time", "end_time", "overtime_hours", "overtime_type", "total_overtime_pay", "reason", "status"],
        order_by="creation desc",
        limit=20
    )

    hd_requests = frappe.get_all(
        "Employee Half Day Request",
        fields=["name", "employee", "employee_name", "department", "date", "half_day_session", "leave_type", "reason", "status"],
        order_by="creation desc",
        limit=20
    )

    return {
        "overtime_requests": ot_requests,
        "half_day_requests": hd_requests
    }

@frappe.whitelist()
def process_request_action(
    doctype: str,
    docname: str,
    action: str,
    rejection_reason: Optional[str] = None
) -> Dict[str, Any]:
    if not frappe.has_permission(doctype, "write"):
        frappe.throw("You do not have permission to manage this request.", frappe.PermissionError)

    doc = frappe.get_doc(doctype, docname)
    if action == "approve":
        doc.approve()
        return {"status": "success", "message": f"{doctype} {docname} approved."}
    elif action == "reject":
        doc.reject(reason=rejection_reason)
        return {"status": "success", "message": f"{doctype} {docname} rejected."}
    else:
        frappe.throw("Invalid action.")

@frappe.whitelist()
def quick_submit_overtime(
    employee: str,
    overtime_date: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    overtime_hours: float = 0.0,
    reason: Optional[str] = None,
    overtime_type: str = "Regular Overtime",
    hourly_rate: float = 0.0
) -> Dict[str, Any]:
    doc = frappe.get_doc({
        "doctype": "Employee Overtime Request",
        "employee": employee,
        "overtime_date": overtime_date or nowdate(),
        "start_time": start_time,
        "end_time": end_time,
        "overtime_hours": flt(overtime_hours),
        "hourly_rate": flt(hourly_rate),
        "reason": reason,
        "overtime_type": overtime_type,
        "status": "Pending Approval"
    })
    doc.insert()
    return {"status": "success", "name": doc.name, "message": "Overtime request submitted!"}

@frappe.whitelist()
def quick_submit_half_day(
    employee: str,
    date: Optional[str] = None,
    half_day_session: str = "First Half (Morning)",
    reason: Optional[str] = None,
    leave_type: str = "Casual Leave"
) -> Dict[str, Any]:
    doc = frappe.get_doc({
        "doctype": "Employee Half Day Request",
        "employee": employee,
        "date": date or nowdate(),
        "half_day_session": half_day_session,
        "leave_type": leave_type,
        "reason": reason,
        "status": "Pending Approval"
    })
    doc.insert()
    return {"status": "success", "name": doc.name, "message": "Half Day request submitted!"}

@frappe.whitelist()
def get_employees_dropdown() -> List[Dict[str, Any]]:
    return frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["name", "employee_name", "department"],
        order_by="employee_name asc"
    )

@frappe.whitelist()
def get_departments_list() -> List[Dict[str, Any]]:
    return frappe.get_all("Department", fields=["name"], order_by="name asc")
