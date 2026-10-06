frappe.listview_settings['Job Candidate'] = {
    add_fields: ['candidate_name', 'status', 'position_applied', 'experience_years', 'profile_tags', 'current_location', 'notice_period'],
    onload: function(listview) {
        listview.page.add_inner_button(__('⚡ Boolean Candidate Search & Matcher'), function() {
            window.open('/candidate-search', '_blank');
        });
        listview.page.add_inner_button(__('📋 Public Application Form'), function() {
            window.open('/apply', '_blank');
        });
    }
};
