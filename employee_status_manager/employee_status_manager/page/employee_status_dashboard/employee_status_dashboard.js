frappe.pages['employee_status_dashboard'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('Employee Status & Overtime Hub'),
        single_column: true
    });

    wrapper.employee_status_dashboard = new EmployeeStatusDashboard(page, wrapper);
};

class EmployeeStatusDashboard {
    constructor(page, wrapper) {
        this.page = page;
        this.wrapper = wrapper;
        this.current_date = frappe.datetime.get_today();
        this.active_tab = 'roster';
        this.init();
    }

    init() {
        this.setup_header_buttons();
        this.render_layout();
        this.bind_events();
        this.refresh_all();
    }

    setup_header_buttons() {
        var me = this;
        this.page.set_primary_action(__('New Overtime Request'), function() {
            me.show_new_overtime_modal();
        }, 'octicon octicon-plus');

        this.page.add_secondary_action(__('New Half Day Request'), function() {
            me.show_new_halfday_modal();
        });

        this.page.add_inner_button(__('Refresh'), function() {
            me.refresh_all();
        });
    }

    render_layout() {
        var html = `
        <div class="esm-container">
            <!-- Header Date & Filter Bar -->
            <div class="esm-header-bar">
                <div class="esm-header-title">
                    <h2>Live Attendance & Overtime Command Center</h2>
                    <span class="esm-header-subtitle">Real-time status tracking, half-day leaves & overtime workflow approvals</span>
                </div>
                <div class="esm-header-actions">
                    <div class="esm-date-control">
                        <span>📅 Date:</span>
                        <input type="date" id="esm-filter-date" value="${this.current_date}" />
                    </div>
                </div>
            </div>

            <!-- KPI Cards -->
            <div class="esm-kpi-grid">
                <div class="esm-kpi-card">
                    <div class="esm-kpi-icon esm-icon-blue">👥</div>
                    <div class="esm-kpi-content">
                        <span class="esm-kpi-val" id="kpi-total-emp">--</span>
                        <span class="esm-kpi-label">Active Employees</span>
                    </div>
                </div>
                <div class="esm-kpi-card">
                    <div class="esm-kpi-icon esm-icon-emerald">✅</div>
                    <div class="esm-kpi-content">
                        <span class="esm-kpi-val" id="kpi-present-emp">--</span>
                        <span class="esm-kpi-label">Present Today</span>
                    </div>
                </div>
                <div class="esm-kpi-card">
                    <div class="esm-kpi-icon esm-icon-purple">⏱️</div>
                    <div class="esm-kpi-content">
                        <span class="esm-kpi-val" id="kpi-ot-hours">0h</span>
                        <span class="esm-kpi-label">Overtime Logged</span>
                    </div>
                </div>
                <div class="esm-kpi-card">
                    <div class="esm-kpi-icon esm-icon-amber">🌓</div>
                    <div class="esm-kpi-content">
                        <span class="esm-kpi-val" id="kpi-halfday-emp">--</span>
                        <span class="esm-kpi-label">Half-Day Leaves</span>
                    </div>
                </div>
            </div>

            <!-- Tab Navigation -->
            <div class="esm-nav-tabs">
                <button class="esm-tab-btn active" data-tab="roster">
                    📋 Live Employee Status Board
                </button>
                <button class="esm-tab-btn" data-tab="overtime">
                    ⚡ Overtime Requests
                    <span class="esm-badge-counter" id="badge-ot-pending" style="display:none;">0</span>
                </button>
                <button class="esm-tab-btn" data-tab="halfday">
                    🌓 Half Day Requests
                    <span class="esm-badge-counter" id="badge-hd-pending" style="display:none;">0</span>
                </button>
            </div>

            <!-- Tab Contents -->
            <div id="esm-tab-roster" class="esm-tab-pane">
                <div class="esm-filter-bar">
                    <div class="esm-search-group">
                        <input type="text" id="esm-search-input" class="esm-input" placeholder="🔍 Search employee by name..." />
                        <select id="esm-status-filter" class="esm-select">
                            <option value="All">All Statuses</option>
                            <option value="Present">Present</option>
                            <option value="Overtime">Overtime Active</option>
                            <option value="Half Day">Half Day</option>
                        </select>
                    </div>
                </div>
                <div class="esm-card-wrapper">
                    <table class="esm-table">
                        <thead>
                            <tr>
                                <th>Employee</th>
                                <th>Department</th>
                                <th>Designation</th>
                                <th>Status Today</th>
                                <th>Overtime Hours</th>
                                <th>Notes / Details</th>
                            </tr>
                        </thead>
                        <tbody id="esm-roster-tbody">
                            <tr><td colspan="6" class="text-center text-muted">Loading live status roster...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <div id="esm-tab-overtime" class="esm-tab-pane" style="display:none;">
                <div class="esm-card-wrapper">
                    <table class="esm-table">
                        <thead>
                            <tr>
                                <th>Request ID</th>
                                <th>Employee</th>
                                <th>Date</th>
                                <th>Hours</th>
                                <th>Timing</th>
                                <th>Type</th>
                                <th>Reason</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="esm-overtime-tbody">
                            <tr><td colspan="9" class="text-center text-muted">Loading overtime requests...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <div id="esm-tab-halfday" class="esm-tab-pane" style="display:none;">
                <div class="esm-card-wrapper">
                    <table class="esm-table">
                        <thead>
                            <tr>
                                <th>Request ID</th>
                                <th>Employee</th>
                                <th>Date</th>
                                <th>Session</th>
                                <th>Leave Type</th>
                                <th>Reason</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="esm-halfday-tbody">
                            <tr><td colspan="8" class="text-center text-muted">Loading half day requests...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        `;

        $(this.wrapper).find('.layout-main-section').html(html);
    }

    bind_events() {
        var me = this;

        $(this.wrapper).on('change', '#esm-filter-date', function() {
            me.current_date = $(this).val();
            me.refresh_all();
        });

        $(this.wrapper).on('click', '.esm-tab-btn', function() {
            var tab = $(this).data('tab');
            me.switch_tab(tab);
        });

        $(this.wrapper).on('keyup', '#esm-search-input', function() {
            me.load_roster();
        });
        $(this.wrapper).on('change', '#esm-status-filter', function() {
            me.load_roster();
        });

        $(this.wrapper).on('click', '.btn-approve-ot', function() {
            var name = $(this).data('name');
            me.handle_action('Employee Overtime Request', name, 'approve');
        });
        $(this.wrapper).on('click', '.btn-reject-ot', function() {
            var name = $(this).data('name');
            me.prompt_reject('Employee Overtime Request', name);
        });

        $(this.wrapper).on('click', '.btn-approve-hd', function() {
            var name = $(this).data('name');
            me.handle_action('Employee Half Day Request', name, 'approve');
        });
        $(this.wrapper).on('click', '.btn-reject-hd', function() {
            var name = $(this).data('name');
            me.prompt_reject('Employee Half Day Request', name);
        });
    }

    switch_tab(tab) {
        this.active_tab = tab;
        $(this.wrapper).find('.esm-tab-btn').removeClass('active');
        $(this.wrapper).find(`.esm-tab-btn[data-tab="${tab}"]`).addClass('active');

        $(this.wrapper).find('.esm-tab-pane').hide();
        $(this.wrapper).find(`#esm-tab-${tab}`).show();
    }

    refresh_all() {
        this.load_stats();
        this.load_roster();
        this.load_requests();
    }

    load_stats() {
        var me = this;
        frappe.call({
            method: 'employee_status_manager.api.get_dashboard_stats',
            args: { date: me.current_date },
            callback: function(r) {
                if (r.message) {
                    var s = r.message;
                    $('#kpi-total-emp').text(s.total_employees);
                    $('#kpi-present-emp').text(s.present_count);
                    $('#kpi-ot-hours').text(s.total_ot_hours + 'h (' + s.overtime_count + ')');
                    $('#kpi-halfday-emp').text(s.half_day_count);

                    if (s.pending_overtime > 0) {
                        $('#badge-ot-pending').text(s.pending_overtime).show();
                    } else {
                        $('#badge-ot-pending').hide();
                    }

                    if (s.pending_half_day > 0) {
                        $('#badge-hd-pending').text(s.pending_half_day).show();
                    } else {
                        $('#badge-hd-pending').hide();
                    }
                }
            }
        });
    }

    load_roster() {
        var me = this;
        var search = $('#esm-search-input').val();
        var status_filter = $('#esm-status-filter').val();

        frappe.call({
            method: 'employee_status_manager.api.get_employee_roster',
            args: {
                date: me.current_date,
                status_filter: status_filter,
                search: search
            },
            callback: function(r) {
                var tbody = $('#esm-roster-tbody');
                tbody.empty();
                var list = r.message || [];
                if (!list.length) {
                    tbody.html('<tr><td colspan="6" class="esm-empty-state">No employees found for the selected filter.</td></tr>');
                    return;
                }

                list.forEach(function(emp) {
                    var badgeClass = 'esm-badge-present';
                    var icon = '🟢';
                    if (emp.status === 'Overtime Active') {
                        badgeClass = 'esm-badge-overtime';
                        icon = '⏱️';
                    } else if (emp.status.indexOf('Half Day') !== -1) {
                        badgeClass = 'esm-badge-halfday';
                        icon = '🌓';
                    }

                    var initials = emp.employee_name ? emp.employee_name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() : 'EM';

                    var row = `
                        <tr>
                            <td>
                                <div class="esm-emp-cell">
                                    <div class="esm-avatar">${initials}</div>
                                    <div class="esm-emp-info">
                                        <span class="esm-emp-name">${emp.employee_name}</span>
                                        <span class="esm-emp-id">${emp.employee}</span>
                                    </div>
                                </div>
                            </td>
                            <td>${emp.department || '-'}</td>
                            <td>${emp.designation || '-'}</td>
                            <td>
                                <span class="esm-badge ${badgeClass}">${icon} ${emp.status}</span>
                            </td>
                            <td>
                                ${emp.overtime_hours > 0 ? `<strong>${emp.overtime_hours} hrs</strong>` : '-'}
                            </td>
                            <td>
                                <span class="text-muted">${emp.details || 'Regular Shift'}</span>
                            </td>
                        </tr>
                    `;
                    tbody.append(row);
                });
            }
        });
    }

    load_requests() {
        var me = this;
        frappe.call({
            method: 'employee_status_manager.api.get_pending_requests',
            callback: function(r) {
                if (!r.message) return;
                var ot_list = r.message.overtime_requests || [];
                var hd_list = r.message.half_day_requests || [];

                // Render Overtime
                var ot_tbody = $('#esm-overtime-tbody');
                ot_tbody.empty();
                if (!ot_list.length) {
                    ot_tbody.html('<tr><td colspan="9" class="esm-empty-state">No overtime requests logged.</td></tr>');
                } else {
                    ot_list.forEach(function(row) {
                        var statusBadge = row.status === 'Approved' ? 'esm-badge-approved' : (row.status === 'Rejected' ? 'esm-badge-rejected' : 'esm-badge-pending');
                        var actionHtml = (row.status === 'Pending Approval' || row.status === 'Draft') ? `
                            <button class="esm-btn-action esm-btn-approve btn-approve-ot" data-name="${row.name}">Approve</button>
                            <button class="esm-btn-action esm-btn-reject btn-reject-ot" data-name="${row.name}">Reject</button>
                        ` : `<span class="text-muted">${row.status}</span>`;

                        ot_tbody.append(`
                            <tr>
                                <td><a href="/app/employee-overtime-request/${row.name}">${row.name}</a></td>
                                <td><strong>${row.employee_name}</strong><br><small class="text-muted">${row.employee}</small></td>
                                <td>${row.overtime_date}</td>
                                <td><strong>${row.overtime_hours} hrs</strong></td>
                                <td><small>${row.start_time} - ${row.end_time}</small></td>
                                <td>${row.overtime_type}</td>
                                <td><small>${row.reason || '-'}</small></td>
                                <td><span class="esm-badge ${statusBadge}">${row.status}</span></td>
                                <td>${actionHtml}</td>
                            </tr>
                        `);
                    });
                }

                // Render Half Day
                var hd_tbody = $('#esm-halfday-tbody');
                hd_tbody.empty();
                if (!hd_list.length) {
                    hd_tbody.html('<tr><td colspan="8" class="esm-empty-state">No half-day requests logged.</td></tr>');
                } else {
                    hd_list.forEach(function(row) {
                        var statusBadge = row.status === 'Approved' ? 'esm-badge-approved' : (row.status === 'Rejected' ? 'esm-badge-rejected' : 'esm-badge-pending');
                        var actionHtml = (row.status === 'Pending Approval' || row.status === 'Draft') ? `
                            <button class="esm-btn-action esm-btn-approve btn-approve-hd" data-name="${row.name}">Approve</button>
                            <button class="esm-btn-action esm-btn-reject btn-reject-hd" data-name="${row.name}">Reject</button>
                        ` : `<span class="text-muted">${row.status}</span>`;

                        hd_tbody.append(`
                            <tr>
                                <td><a href="/app/employee-half-day-request/${row.name}">${row.name}</a></td>
                                <td><strong>${row.employee_name}</strong><br><small class="text-muted">${row.employee}</small></td>
                                <td>${row.date}</td>
                                <td><strong>${row.half_day_session}</strong></td>
                                <td>${row.leave_type}</td>
                                <td><small>${row.reason || '-'}</small></td>
                                <td><span class="esm-badge ${statusBadge}">${row.status}</span></td>
                                <td>${actionHtml}</td>
                            </tr>
                        `);
                    });
                }
            }
        });
    }

    handle_action(doctype, docname, action, reason) {
        var me = this;
        frappe.call({
            method: 'employee_status_manager.api.process_request_action',
            args: {
                doctype: doctype,
                docname: docname,
                action: action,
                rejection_reason: reason
            },
            callback: function(r) {
                if (!r.exc) {
                    frappe.show_alert({
                        message: action === 'approve' ? __('Request approved successfully!') : __('Request rejected.'),
                        indicator: action === 'approve' ? 'green' : 'orange'
                    });
                    me.refresh_all();
                }
            }
        });
    }

    prompt_reject(doctype, docname) {
        var me = this;
        frappe.prompt([
            {
                fieldname: 'reason',
                fieldtype: 'Small Text',
                label: __('Rejection Reason'),
                reqd: 1
            }
        ], function(values) {
            me.handle_action(doctype, docname, 'reject', values.reason);
        }, __('Reject Request'), __('Confirm Reject'));
    }

    show_new_overtime_modal() {
        var me = this;
        var d = new frappe.ui.Dialog({
            title: __('Quick Overtime Entry'),
            fields: [
                {
                    fieldname: 'employee',
                    fieldtype: 'Link',
                    options: 'Employee',
                    label: __('Employee'),
                    reqd: 1
                },
                {
                    fieldname: 'overtime_date',
                    fieldtype: 'Date',
                    label: __('Overtime Date'),
                    default: me.current_date,
                    reqd: 1
                },
                {
                    fieldname: 'col_1',
                    fieldtype: 'Column Break'
                },
                {
                    fieldname: 'overtime_type',
                    fieldtype: 'Select',
                    options: 'Regular Overtime\nWeekend Overtime\nHoliday Overtime\nEmergency Support',
                    label: __('Overtime Type'),
                    default: 'Regular Overtime'
                },
                {
                    fieldname: 'sec_1',
                    fieldtype: 'Section Break',
                    label: __('Timing')
                },
                {
                    fieldname: 'start_time',
                    fieldtype: 'Time',
                    label: __('Start Time'),
                    default: '18:00:00',
                    reqd: 1
                },
                {
                    fieldname: 'end_time',
                    fieldtype: 'Time',
                    label: __('End Time'),
                    default: '21:00:00',
                    reqd: 1
                },
                {
                    fieldname: 'col_2',
                    fieldtype: 'Column Break'
                },
                {
                    fieldname: 'overtime_hours',
                    fieldtype: 'Float',
                    label: __('Overtime Hours'),
                    default: 3.0,
                    reqd: 1
                },
                {
                    fieldname: 'sec_2',
                    fieldtype: 'Section Break'
                },
                {
                    fieldname: 'reason',
                    fieldtype: 'Small Text',
                    label: __('Reason / Task Done'),
                    reqd: 1
                }
            ],
            primary_action_label: __('Submit Overtime'),
            primary_action: function(values) {
                frappe.call({
                    method: 'employee_status_manager.api.quick_submit_overtime',
                    args: values,
                    callback: function(r) {
                        if (!r.exc) {
                            frappe.show_alert({message: __('Overtime Request Submitted!'), indicator: 'green'});
                            d.hide();
                            me.refresh_all();
                        }
                    }
                });
            }
        });
        d.show();
    }

    show_new_halfday_modal() {
        var me = this;
        var d = new frappe.ui.Dialog({
            title: __('Quick Half Day Request'),
            fields: [
                {
                    fieldname: 'employee',
                    fieldtype: 'Link',
                    options: 'Employee',
                    label: __('Employee'),
                    reqd: 1
                },
                {
                    fieldname: 'date',
                    fieldtype: 'Date',
                    label: __('Date'),
                    default: me.current_date,
                    reqd: 1
                },
                {
                    fieldname: 'col_1',
                    fieldtype: 'Column Break'
                },
                {
                    fieldname: 'half_day_session',
                    fieldtype: 'Select',
                    options: 'First Half (Morning)\nSecond Half (Afternoon)',
                    label: __('Half Day Session'),
                    default: 'First Half (Morning)',
                    reqd: 1
                },
                {
                    fieldname: 'leave_type',
                    fieldtype: 'Select',
                    options: 'Casual Leave\nSick Leave\nPrivilege Leave\nCompensatory Off\nUnpaid Leave',
                    label: __('Leave Type'),
                    default: 'Casual Leave'
                },
                {
                    fieldname: 'sec_1',
                    fieldtype: 'Section Break'
                },
                {
                    fieldname: 'reason',
                    fieldtype: 'Small Text',
                    label: __('Reason for Half Day'),
                    reqd: 1
                }
            ],
            primary_action_label: __('Submit Half Day'),
            primary_action: function(values) {
                frappe.call({
                    method: 'employee_status_manager.api.quick_submit_half_day',
                    args: values,
                    callback: function(r) {
                        if (!r.exc) {
                            frappe.show_alert({message: __('Half Day Request Submitted!'), indicator: 'green'});
                            d.hide();
                            me.refresh_all();
                        }
                    }
                });
            }
        });
        d.show();
    }
}
