frappe.ui.form.on('Employee Half Day Request', {
    refresh: function(frm) {
        if (!frm.is_new() && (frm.doc.status === "Pending Approval" || frm.doc.status === "Draft") && frappe.user.has_role(["System Manager", "HR Manager", "HR User"])) {
            frm.add_custom_button(__('Approve'), function() {
                frappe.call({
                    method: 'approve',
                    doc: frm.doc,
                    callback: function(r) {
                        if (!r.exc) {
                            frappe.show_alert({message: __('Half Day request approved successfully!'), indicator: 'green'});
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
                                frappe.show_alert({message: __('Half Day request rejected.'), indicator: 'orange'});
                                frm.reload_doc();
                            }
                        }
                    });
                }, __('Reject Half Day Request'), __('Reject'));
            }, __('Actions')).addClass('btn-danger');
        }
    }
});
