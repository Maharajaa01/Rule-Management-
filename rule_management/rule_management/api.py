import frappe
from frappe import _
import json

def return_success(data=None, message="Success"):
    return {"status": "success", "message": message, "data": data}

def return_error(message, status_code=400):
    frappe.local.response['http_status_code'] = status_code
    return {"status": "error", "message": message}

def is_admin():
    return "Administrator" in frappe.get_roles(frappe.session.user)

def get_staff_profile(user=None):
    if not user:
        user = frappe.session.user
    staff = frappe.db.get_all("Staff Master", filters={"user": user, "status": "Active"}, fields=["name", "employee_name", "staff_category"])
    if not staff:
        frappe.throw(_("Staff profile not found for current user."), frappe.PermissionError)
    return staff[0]

# --- Authentication ---
@frappe.whitelist(allow_guest=True)
def login(login_id, password):
    try:
        # Check Staff Master
        staff = frappe.db.get_all("Staff Master", filters={"login_id": login_id, "status": "Active"}, fields=["name", "user"])
        if not staff:
            return return_error("Invalid login credentials or inactive account", 401)
        
        staff_name = staff[0].name
        
        # Verify password (handles both Data and Password fieldtypes depending on frappe version implementation)
        try:
            saved_password = frappe.get_password("Staff Master", staff_name, "password")
        except Exception:
            saved_password = frappe.db.get_value("Staff Master", staff_name, "password")
            
        if saved_password != password:
            return return_error("Invalid login credentials", 401)
        
        user = staff[0].user
        if not user:
            return return_error("No system user linked to this staff profile", 400)
            
        # Log in the user via Frappe's LoginManager to establish session
        from frappe.auth import LoginManager
        frappe.local.login_manager = LoginManager()
        frappe.local.login_manager.login_as(user)
        
        return return_success({"staff_id": staff_name, "user": user}, "Login successful")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Rule Management Login API")
        return return_error(str(e), 500)

# --- Staff APIs ---
@frappe.whitelist()
def get_logged_in_staff_profile():
    try:
        staff = get_staff_profile()
        doc = frappe.get_doc("Staff Master", staff.name)
        return return_success(doc.as_dict())
    except frappe.PermissionError as e:
        return return_error(str(e), 403)
    except Exception as e:
        return return_error(str(e), 500)

@frappe.whitelist()
def get_staff_dashboard():
    try:
        staff = get_staff_profile()
        doc = frappe.get_doc("Staff Master", staff.name)
        
        categories = [d.rule_category for d in doc.assigned_categories]
        total_categories = len(categories)
        
        if not categories:
            return return_success({"total_assigned_categories": 0, "total_assigned_rule_books": 0, "total_rules": 0})
            
        rule_books = frappe.db.get_all("Rule Book", filters={"rule_category": ("in", categories), "is_active": 1})
        total_rule_books = len(rule_books)
        
        rule_book_names = [rb.name for rb in rule_books]
        if not rule_book_names:
            total_rules = 0
        else:
            total_rules = frappe.db.count("Rule List", filters={"parent": ("in", rule_book_names)})
            
        return return_success({
            "total_assigned_categories": total_categories,
            "total_assigned_rule_books": total_rule_books,
            "total_rules": total_rules
        })
    except frappe.PermissionError as e:
        return return_error(str(e), 403)
    except Exception as e:
        return return_error(str(e), 500)

@frappe.whitelist()
def get_assigned_rule_categories():
    try:
        staff = get_staff_profile()
        doc = frappe.get_doc("Staff Master", staff.name)
        categories = [d.rule_category for d in doc.assigned_categories]
        
        if not categories:
            return return_success([])
            
        cats = frappe.db.get_all("Rule Category", filters={"name": ("in", categories), "is_active": 1}, fields=["name", "category_name", "icon", "description"])
        return return_success(cats)
    except frappe.PermissionError as e:
        return return_error(str(e), 403)
    except Exception as e:
        return return_error(str(e), 500)

@frappe.whitelist()
def get_rule_books(rule_category):
    try:
        if not rule_category:
            return return_error("Rule Category is required", 400)
            
        staff = get_staff_profile()
        doc = frappe.get_doc("Staff Master", staff.name)
        categories = [d.rule_category for d in doc.assigned_categories]
        
        if rule_category not in categories:
            return return_error("You do not have permission to access this category", 403)
            
        books = frappe.db.get_all("Rule Book", filters={"rule_category": rule_category, "is_active": 1}, fields=["name", "rule_book_name", "icon", "description"])
        return return_success(books)
    except frappe.PermissionError as e:
        return return_error(str(e), 403)
    except Exception as e:
        return return_error(str(e), 500)

@frappe.whitelist()
def get_rule_book_detail(rule_book):
    try:
        if not rule_book:
            return return_error("Rule Book is required", 400)
            
        staff = get_staff_profile()
        doc = frappe.get_doc("Staff Master", staff.name)
        categories = [d.rule_category for d in doc.assigned_categories]
        
        book_doc = frappe.get_doc("Rule Book", rule_book)
        if book_doc.rule_category not in categories:
            return return_error("You do not have permission to access this rule book", 403)
            
        if not book_doc.is_active:
            return return_error("This rule book is inactive", 400)
            
        return return_success({
            "rule_book": book_doc.rule_book_name,
            "youtube_url": book_doc.youtube_url,
            "audio_file": book_doc.audio_file,
            "rules": [{"idx": r.idx_no, "rule": r.rule} for r in book_doc.rules]
        })
    except frappe.DoesNotExistError:
        return return_error("Rule book not found", 404)
    except frappe.PermissionError as e:
        return return_error(str(e), 403)
    except Exception as e:
        return return_error(str(e), 500)

# --- Admin APIs ---
def admin_only():
    if not is_admin():
        frappe.throw(_("Not permitted. Administrator access required."), frappe.PermissionError)

@frappe.whitelist()
def admin_dashboard():
    try:
        admin_only()
        return return_success({
            "total_staff": frappe.db.count("Staff Master"),
            "total_staff_categories": frappe.db.count("Staff Category"),
            "total_rule_categories": frappe.db.count("Rule Category"),
            "total_rule_books": frappe.db.count("Rule Book")
        })
    except frappe.PermissionError as e:
        return return_error(str(e), 403)
    except Exception as e:
        return return_error(str(e), 500)

# CRUD Helper
def handle_crud(doctype, action, doc_id=None, data=None):
    admin_only()
    if action == "create":
        if isinstance(data, str):
            data = json.loads(data)
        doc = frappe.get_doc({"doctype": doctype, **data})
        doc.insert(ignore_permissions=True)
        return return_success(doc.as_dict(), f"{doctype} created successfully")
    elif action == "update":
        if not doc_id:
            return return_error(f"{doctype} ID required for update", 400)
        if isinstance(data, str):
            data = json.loads(data)
        doc = frappe.get_doc(doctype, doc_id)
        doc.update(data)
        doc.save(ignore_permissions=True)
        return return_success(doc.as_dict(), f"{doctype} updated successfully")
    elif action == "delete":
        if not doc_id:
            return return_error(f"{doctype} ID required for delete", 400)
        frappe.delete_doc(doctype, doc_id, ignore_permissions=True)
        return return_success(None, f"{doctype} deleted successfully")

# Staff CRUD
@frappe.whitelist()
def create_staff(data):
    try:
        return handle_crud("Staff Master", "create", data=data)
    except Exception as e:
        return return_error(str(e), 500)

@frappe.whitelist()
def update_staff(staff_id, data):
    try:
        return handle_crud("Staff Master", "update", doc_id=staff_id, data=data)
    except Exception as e:
        return return_error(str(e), 500)

@frappe.whitelist()
def delete_staff(staff_id):
    try:
        return handle_crud("Staff Master", "delete", doc_id=staff_id)
    except Exception as e:
        return return_error(str(e), 500)

# Rule Category CRUD
@frappe.whitelist()
def create_rule_category(data):
    try:
        return handle_crud("Rule Category", "create", data=data)
    except Exception as e:
        return return_error(str(e), 500)

@frappe.whitelist()
def update_rule_category(category_id, data):
    try:
        return handle_crud("Rule Category", "update", doc_id=category_id, data=data)
    except Exception as e:
        return return_error(str(e), 500)

@frappe.whitelist()
def delete_rule_category(category_id):
    try:
        return handle_crud("Rule Category", "delete", doc_id=category_id)
    except Exception as e:
        return return_error(str(e), 500)

# Rule Book CRUD
@frappe.whitelist()
def create_rule_book(data):
    try:
        return handle_crud("Rule Book", "create", data=data)
    except Exception as e:
        return return_error(str(e), 500)

@frappe.whitelist()
def update_rule_book(book_id, data):
    try:
        return handle_crud("Rule Book", "update", doc_id=book_id, data=data)
    except Exception as e:
        return return_error(str(e), 500)

@frappe.whitelist()
def delete_rule_book(book_id):
    try:
        return handle_crud("Rule Book", "delete", doc_id=book_id)
    except Exception as e:
        return return_error(str(e), 500)
