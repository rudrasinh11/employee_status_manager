import frappe
from frappe import _
from frappe.model.document import Document
import re

class JobCandidate(Document):
    def validate(self):
        # 1. Clean and normalize inputs
        if self.candidate_name:
            self.candidate_name = self.candidate_name.strip()
        if self.email:
            self.email = self.email.strip().lower()
        if self.phone:
            # Keep numbers and plus
            cleaned_phone = re.sub(r'[^0-9+]', '', str(self.phone))
            if len(cleaned_phone.replace('+', '')) < 10:
                frappe.throw(_("Phone number must have at least 10 digits."))
            self.phone = cleaned_phone

        # 2. STRICT PDF VALIDATION (No .doc, .docx, images, etc.)
        if self.resume:
            clean_resume = str(self.resume).strip().lower()
            # Strip query params if any
            clean_resume = clean_resume.split('?')[0]

            # Check prohibited document types explicitly
            if clean_resume.endswith('.doc') or clean_resume.endswith('.docx'):
                frappe.throw(_("Word documents (.doc, .docx) are NOT allowed. Please upload your resume in PDF format only (.pdf)."))
            
            if not clean_resume.endswith('.pdf'):
                frappe.throw(_("Invalid resume file format! Strictly PDF format (.pdf) is accepted."))
