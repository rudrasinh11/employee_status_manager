import frappe
from frappe.model.document import Document
from frappe.utils import nowdate

class EmployeeHalfDayRequest(Document):
    def validate(self):
        if self.docstatus == 0 and not self.status:
            self.status = "Draft"

    def on_submit(self):
        if self.status == "Draft":
            self.db_set("status", "Pending Approval")

    def on_cancel(self):
        self.db_set("status", "Cancelled")

    @frappe.whitelist()
    def approve(self):
        self.status = "Approved"
        self.approver = frappe.session.user
        self.approval_date = nowdate()
        self.save(ignore_permissions=True)
        self.update_daily_status()
        return True

    @frappe.whitelist()
    def reject(self, reason=None):
        self.status = "Rejected"
        self.approver = frappe.session.user
        self.approval_date = nowdate()
        if reason:
            self.rejection_reason = reason
        self.save(ignore_permissions=True)
        return True

    def update_daily_status(self):
        try:
            status_text = "Half Day (First Half)" if "First Half" in (self.half_day_session or "") else "Half Day (Second Half)"
            status_records = frappe.get_all(
                "Employee Daily Status",
                filters={"employee": self.employee, "date": self.date},
                fields=["name"]
            )
            if status_records:
                doc = frappe.get_doc("Employee Daily Status", status_records[0].name)
                doc.status = status_text
                doc.remarks = f"{self.half_day_session} Approved ({self.leave_type})"
                doc.save(ignore_permissions=True)
            else:
                doc = frappe.get_doc({
                    "doctype": "Employee Daily Status",
                    "employee": self.employee,
                    "date": self.date,
                    "status": status_text,
                    "remarks": f"{self.half_day_session} Approved ({self.leave_type})"
                })
                doc.insert(ignore_permissions=True)
        except Exception:
            pass
