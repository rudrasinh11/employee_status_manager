frappe.pages['face_kiosk'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('Face & PIN Attendance Kiosk'),
        single_column: true
    });

    page.set_primary_action(__('Open Fullscreen Kiosk ↗'), function() {
        window.open('/face-attendance', '_blank');
    }, 'camera');

    page.add_inner_button(__('Refresh Stream'), function() {
        var iframe = wrapper.querySelector('iframe');
        if (iframe) iframe.src = '/face-attendance?ts=' + Date.now();
    });

    $(wrapper).find('.layout-main-section').html(
        '<div style="width: 100%; height: calc(100vh - 140px); border-radius: 16px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.3); border: 1px solid var(--border-color);">' +
        '  <iframe src="/face-attendance" allow="camera; microphone; geolocation" style="width: 100%; height: 100%; border: none;"></iframe>' +
        '</div>'
    );
};
