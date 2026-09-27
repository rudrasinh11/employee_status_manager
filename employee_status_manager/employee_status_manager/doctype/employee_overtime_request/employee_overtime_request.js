frappe.ui.form.on('Employee Overtime Request', {
    refresh: function(frm) {
        if (!frm.is_new() && (frm.doc.status === "Pending Approval" || frm.doc.status === "Draft") && frappe.user.has_role(["System Manager", "HR Manager", "HR User"])) {
            frm.add_custom_button(__('Approve'), function() {
                frappe.call({
                    method: 'approve',
                    doc: frm.doc,
                    callback: function(r) {
                        if (!r.exc) {
                            frappe.show_alert({message: __('Overtime request approved successfully!'), indicator: 'green'});
                            frm.reload_doc();
                        }
                    }
                });
            }, __('Actions')).addClass('btn-primary');

            frm.add_custom_button(__('Reject'), function() {
                frappe.prompt([
                    {
                        fieldtype: 'Small Text',
                        fieldname: 'reason',
                        label: __('Reason for Rejection'),
                        reqd: 1
                    }
                ], function(values) {
                    frappe.call({
                        method: 'reject',
                        doc: frm.doc,
                        args: { reason: values.reason },
                        callback: function(r) {
                            if (!r.exc) {
                                frappe.show_alert({message: __('Overtime request rejected.'), indicator: 'orange'});
                                frm.reload_doc();
                            }
                        }
                    });
                }, __('Reject Overtime Request'), __('Reject'));
            }, __('Actions')).addClass('btn-danger');
        }
    },

    start_time: function(frm) {
        frm.trigger('calculate_hours');
    },

    end_time: function(frm) {
        frm.trigger('calculate_hours');
    },

    calculate_hours: function(frm) {
        if (frm.doc.start_time && frm.doc.end_time) {
            let start = frm.doc.start_time.split(':');
            let end = frm.doc.end_time.split(':');
            let start_h = parseFloat(start[0]) + parseFloat(start[1])/60;
            let end_h = parseFloat(end[0]) + parseFloat(end[1])/60;
            let diff = end_h - start_h;
            if (diff < 0) diff += 24;
            frm.set_value('overtime_hours', Math.round(diff * 100) / 100);
        }
    },

    hourly_rate: function(frm) {
        if (frm.doc.overtime_hours && frm.doc.hourly_rate) {
            frm.set_value('total_overtime_pay', frm.doc.overtime_hours * frm.doc.hourly_rate);
        }
    },

    overtime_hours: function(frm) {
        if (frm.doc.overtime_hours && frm.doc.hourly_rate) {
            frm.set_value('total_overtime_pay', frm.doc.overtime_hours * frm.doc.hourly_rate);
        }
    }
});
