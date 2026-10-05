frappe.ui.form.on('Job Candidate', {
    refresh: function(frm) {
        if (!frm.is_new()) {
            // Quick Follow-Up Actions
            if (frm.doc.phone) {
                // Clean phone for whatsapp
                let cleanPhone = frm.doc.phone.replace(/[^0-9]/g, '');
                if (cleanPhone.length === 10) cleanPhone = '91' + cleanPhone; // Default country code if 10 digits

                frm.add_custom_button(__('WhatsApp Candidate'), function() {
                    let msg = encodeURIComponent(`Hello ${frm.doc.candidate_name}, this is from HR regarding your application for ${frm.doc.position_applied}.`);
                    window.open(`https://wa.me/${cleanPhone}?text=${msg}`, '_blank');
                }, __('Fast Follow-Up'));

                frm.add_custom_button(__('Call Phone'), function() {
                    window.open(`tel:${frm.doc.phone}`, '_self');
                }, __('Fast Follow-Up'));
            }

            if (frm.doc.email) {
                frm.add_custom_button(__('Send Email'), function() {
                    let subject = encodeURIComponent(`Regarding your application for ${frm.doc.position_applied}`);
                    window.open(`mailto:${frm.doc.email}?subject=${subject}`, '_self');
                }, __('Fast Follow-Up'));
            }

            // Quick Status Actions
            if (frm.doc.status === 'New') {
                frm.add_custom_button(__('Move to Screening'), function() {
                    frm.set_value('status', 'Screening');
                    frm.save();
                }, __('Recruitment Status'));
            } else if (frm.doc.status === 'Screening') {
                frm.add_custom_button(__('Schedule Interview'), function() {
                    frm.set_value('status', 'Interview');
                    frm.save();
                }, __('Recruitment Status'));
            }
        }
    }
});
