import frappe

def get_context(context):
    context.no_cache = 1
    context.title = "Smart Face & PIN Attendance"
    context.show_sidebar = False
    return context
