from frappe.model.document import Document
import frappe

class FaceAttendanceProfile(Document):
    def validate(self):
        if self.secret_pin:
            self.secret_pin = str(self.secret_pin).strip()
            if not self.secret_pin.isdigit() or len(self.secret_pin) != 4:
                frappe.throw("PIN must be exactly 4 numeric digits")
