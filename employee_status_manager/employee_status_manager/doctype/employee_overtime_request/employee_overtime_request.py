import frappe
from frappe.model.document import Document
from frappe.utils import time_diff_in_hours, nowdate

class EmployeeOvertimeRequest(Document):
    def validate(self):
        self.calculate_hours()
        self.calculate_pay()
        if self.docstatus == 0 and not self.status:
            self.status = "Draft"

    def calculate_hours(self):
        if self.start_time and self.end_time:
            try:
                diff = time_diff_in_hours(self.end_time, self.start_time)
                if diff < 0:
                    diff += 24.0
                if not self.overtime_hours or self.overtime_hours == 0:
                    self.overtime_hours = round(diff, 2)
            except Exception:
                pass
        if self.overtime_hours and self.overtime_hours > 24:
            frappe.throw("Overtime hours cannot exceed 24 hours in a single day.")

    def calculate_pay(self):
        if self.overtime_hours and self.hourly_rate:
            self.total_overtime_pay = round(float(self.overtime_hours) * float(self.hourly_rate), 2)
        else:
            self.total_overtime_pay = 0.0

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
            status_records = frappe.get_all(
                "Employee Daily Status",
                filters={"employee": self.employee, "date": self.overtime_date},
                fields=["name", "overtime_hours"]
            )
            if status_records:
                doc = frappe.get_doc("Employee Daily Status", status_records[0].name)
                doc.status = "Overtime Active"
                doc.overtime_hours = (doc.overtime_hours or 0) + (self.overtime_hours or 0)
                doc.save(ignore_permissions=True)
            else:
                doc = frappe.get_doc({
                    "doctype": "Employee Daily Status",
                    "employee": self.employee,
                    "date": self.overtime_date,
                    "status": "Overtime Active",
                    "overtime_hours": self.overtime_hours,
                    "remarks": f"Overtime Approved: {self.name}"
                })
                doc.insert(ignore_permissions=True)
        except Exception:
            pass
