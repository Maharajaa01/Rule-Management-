import frappe
from frappe import _
import json

def return_success(data=None, message="Success"):
    return {"status": "success", "message": message, "data": data}

def return_error(message, status_code=400):
    frappe.local.response['http_status_code'] = status_code
    return {"status": "error", "message": message}

def is_admin():
    if frappe.session.user == "Administrator":
        return True
    
    try:
        staff = get_staff_profile()
        return staff.staff_category == "Admin"
    except Exception:
        return False

def get_staff_profile(user=None):
    if not user:
        user = frappe.session.user
        
    # Use request-local caching to prevent duplicate queries for the same user profile
    cache_key = f"staff_profile_{user}"
    if hasattr(frappe.local, cache_key):
        return getattr(frappe.local, cache_key)
        
    staff = frappe.db.get_all("Staff Master", filters={"user": user, "status": "Active"}, fields=["name", "employee_name", "staff_category", "access"], ignore_permissions=True)
    if not staff:
        frappe.throw(_("Staff profile not found for current user."), frappe.PermissionError)
        
    setattr(frappe.local, cache_key, staff[0])
    return staff[0]

# --- Authentication ---
@frappe.whitelist(allow_guest=True)
def login(login_id, password):
    try:
        from frappe.auth import LoginManager
        
        # Populate form_dict so LoginManager can authenticate the user natively
        frappe.local.form_dict.usr = login_id
        frappe.local.form_dict.pwd = password
        
        try:
            login_manager = LoginManager()
            login_manager.authenticate()
            login_manager.post_login()
        except frappe.exceptions.AuthenticationError:
            return return_error("Invalid login credentials", 401)
            
        user = frappe.session.user
        
        # Check Staff Master to ensure the logged-in user is an active staff
        staff = frappe.db.get_all("Staff Master", filters={"user": user, "status": "Active"}, fields=["name", "employee_name", "staff_category", "access"], ignore_permissions=True)
        if not staff:
            # Logout if they aren't an active staff member
            frappe.local.login_manager.logout()
            return return_error("Active staff profile not found for this user", 401)
        
        staff_id = staff[0].name
        employee_name = staff[0].employee_name
        staff_category = staff[0].staff_category
        staff_access = staff[0].access or "View Only"
        
        return return_success({
            "staff_id": staff_id, 
            "employee_name": employee_name,
            "user": user,
            "role": "Administrator" if staff_category == "Admin" else "Staff",
            "access": staff_access
        }, "Login successful")
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Rule Management Login API")
        return return_error(str(e), 500)

# --- Staff APIs ---
@frappe.whitelist(allow_guest=True)
def reset_password(new_password):
    try:
        user = frappe.session.user
        if user == "Guest":
            return return_error("Not logged in", 401)
            
        doc = frappe.get_doc("User", user)
        doc.new_password = new_password
        doc.save(ignore_permissions=True)
        return return_success(None, "Password updated successfully")
    except Exception as e:
        return return_error(str(e), 500)
@frappe.whitelist(allow_guest=True)
def get_logged_in_staff_profile():
    try:
        staff = get_staff_profile()
        doc = frappe.get_doc("Staff Master", staff.name)
        return return_success(doc.as_dict())
    except frappe.PermissionError as e:
        return return_error(str(e), 403)
    except Exception as e:
        return return_error(str(e), 500)

@frappe.whitelist(allow_guest=True)
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

@frappe.whitelist(allow_guest=True)
def get_assigned_rule_categories():
    try:
        if is_admin():
            cats = frappe.db.get_all("Rule Category", filters={"is_active": 1}, fields=["name", "category_name", "description", "is_parent", "parent_category"])
        else:
            staff = get_staff_profile()
            doc = frappe.get_doc("Staff Master", staff.name)
            categories = [d.rule_category for d in doc.assigned_categories]
            
            if not categories:
                return return_success([])
                
            # Fetch directly assigned categories AND their children
            cats = frappe.db.get_all("Rule Category", 
                filters={"is_active": 1}, 
                or_filters={"name": ("in", categories), "parent_category": ("in", categories)},
                fields=["name", "category_name", "description", "is_parent", "parent_category"]
            )
            
        # Format for frontend
        formatted = [{"id": c.name, "category_name": c.category_name, "description": c.description, "is_parent": c.is_parent, "parent_category": c.parent_category} for c in cats]
        return return_success(formatted)
    except frappe.PermissionError as e:
        return return_error(str(e), 403)
    except Exception as e:
        return return_error(str(e), 500)

@frappe.whitelist(allow_guest=True)
def get_rule_books(rule_category=None):
    try:
        filters = {"is_active": 1}
        
        if not is_admin():
            staff = get_staff_profile()
            doc = frappe.get_doc("Staff Master", staff.name)
            categories = [d.rule_category for d in doc.assigned_categories]
            
            # Fetch child categories to grant inherited access
            child_cats = frappe.db.get_all("Rule Category", filters={"parent_category": ("in", categories), "is_active": 1}, fields=["name"])
            allowed_categories = categories + [c.name for c in child_cats]
            
            if rule_category and rule_category not in allowed_categories:
                return return_error("You do not have permission to access this category", 403)
                
            if rule_category:
                filters["rule_category"] = rule_category
            else:
                if not allowed_categories:
                    return return_success([])
                filters["rule_category"] = ("in", allowed_categories)
        else:
            if rule_category:
                filters["rule_category"] = rule_category
                
        books = frappe.db.get_all("Rule Book", filters=filters, fields=["name", "rule_book_name", "rule_category", "youtube_url", "audio_file"])
        
        # Batch fetch rules to prevent N+1 queries (1 query instead of fetching doc for each book)
        book_names = [b.name for b in books]
        rules_by_book = {}
        if book_names:
            all_rules = frappe.db.get_all("Rule List", filters={"parent": ("in", book_names)}, fields=["parent", "rule", "idx"], order_by="idx asc")
            for r in all_rules:
                if r.parent not in rules_by_book:
                    rules_by_book[r.parent] = []
                rules_by_book[r.parent].append(r.rule)
        
        formatted = []
        for b in books:
            formatted.append({
                "id": b.name,
                "book_title": b.rule_book_name,
                "rule_category": b.rule_category,
                "youtube_url": b.youtube_url or "",
                "audio_url": b.audio_file or "",
                "rules": rules_by_book.get(b.name, [])
            })
            
        return return_success(formatted)
    except frappe.PermissionError as e:
        return return_error(str(e), 403)
    except Exception as e:
        return return_error(str(e), 500)

@frappe.whitelist(allow_guest=True)
def get_rule_book_detail(rule_book):
    try:
        if not rule_book:
            return return_error("Rule Book is required", 400)
            
        book_doc = frappe.get_doc("Rule Book", rule_book)
        
        if not is_admin():
            staff = get_staff_profile()
            doc = frappe.get_doc("Staff Master", staff.name)
            categories = [d.rule_category for d in doc.assigned_categories]
            
            # Fetch child categories to grant inherited access
            child_cats = frappe.db.get_all("Rule Category", filters={"parent_category": ("in", categories), "is_active": 1}, fields=["name"])
            allowed_categories = categories + [c.name for c in child_cats]
            
            if book_doc.rule_category not in allowed_categories:
                return return_error("You do not have permission to access this rule book", 403)
            
        if not book_doc.is_active:
            return return_error("This rule book is inactive", 400)
            
        return return_success({
            "id": book_doc.name,
            "book_title": book_doc.rule_book_name,
            "rule_category": book_doc.rule_category,
            "youtube_url": book_doc.youtube_url or "",
            "audio_url": book_doc.audio_file or "",
            "rules": [r.rule for r in book_doc.rules]
        })
    except frappe.DoesNotExistError:
        return return_error("Rule book not found", 404)
    except frappe.PermissionError as e:
        return return_error(str(e), 403)
    except Exception as e:
        return return_error(str(e), 500)

# --- Admin APIs ---
def has_admin_panel_access():
    if is_admin():
        return True
    staff = get_staff_profile()
    if getattr(staff, "access", "") in ["Can Edit", "Can Edit and Delete"]:
        return True
    return False

def can_delete():
    if is_admin():
        return True
    staff = get_staff_profile()
    if getattr(staff, "access", "") == "Can Edit and Delete":
        return True
    return False

def admin_only():
    if not has_admin_panel_access():
        frappe.throw(_("Not permitted. Elevated access required."), frappe.PermissionError)

@frappe.whitelist(allow_guest=True)
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

@frappe.whitelist(allow_guest=True)
def get_staff_list():
    try:
        admin_only()
        staff_list = frappe.db.get_all("Staff Master", fields=["name", "employee_name", "user as login_id", "status", "staff_category as role", "mobile_no", "email", "access"])
        
        # Batch fetch assigned rule categories for these staff members
        staff_ids = [s.name for s in staff_list]
        assigned_categories = {}
        if staff_ids:
            cat_docs = frappe.db.get_all("Assigned Rule Category", filters={"parent": ("in", staff_ids)}, fields=["parent", "rule_category"])
            for c in cat_docs:
                if c.parent not in assigned_categories:
                    assigned_categories[c.parent] = []
                assigned_categories[c.parent].append(c.rule_category)
        
        # Format field names to match frontend expectations (id instead of name, role instead of staff_category)
        formatted_list = []
        for staff in staff_list:
            formatted_list.append({
                "id": staff.name,
                "employee_name": staff.employee_name,
                "login_id": staff.login_id,
                "status": staff.status,
                "role": "Administrator" if staff.role == "Admin" else "Staff",
                "access": staff.access or "View Only",
                "mobile_no": staff.mobile_no,
                "email": staff.email,
                "assigned_categories": assigned_categories.get(staff.name, [])
            })
            
        return return_success(formatted_list)
    except frappe.PermissionError as e:
        return return_error(str(e), 403)
    except Exception as e:
        return return_error(str(e), 500)

# CRUD Helper
def handle_crud(doctype, action, doc_id=None, data=None):
    admin_only()
    if action == "create":
        if not can_delete():
            return return_error("Not permitted to create records. 'Can Edit and Delete' (Full Access) required.", 403)
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
        if not can_delete():
            return return_error("Not permitted to delete records. 'Can Edit and Delete' access required.", 403)
        if not doc_id:
            return return_error(f"{doctype} ID required for delete", 400)
        frappe.delete_doc(doctype, doc_id, ignore_permissions=True)
        return return_success(None, f"{doctype} deleted successfully")

# Staff CRUD
@frappe.whitelist(allow_guest=True)
def create_staff(data):
    try:
        if isinstance(data, str):
            data = json.loads(data)
            
        frappe_data = {
            "employee_name": data.get("employee_name"),
            "login_id": data.get("login_id"),
            "status": data.get("status"),
            "role": "Admin" if data.get("role") == "Administrator" else data.get("role"),
            "access": data.get("access"),
            "mobile_no": data.get("mobile_no"),
            "email": data.get("email"),
            "password": data.get("password")
        }
        if "assigned_categories" in data:
            frappe_data["assigned_categories"] = [{"rule_category": c} for c in data.get("assigned_categories", [])]
            
        return handle_crud("Staff Master", "create", data=frappe_data)
    except Exception as e:
        return return_error(str(e), 500)

@frappe.whitelist(allow_guest=True)
def update_staff(staff_id, data):
    try:
        if isinstance(data, str):
            data = json.loads(data)
            
        frappe_data = {
            "employee_name": data.get("employee_name"),
            "login_id": data.get("login_id"),
            "status": data.get("status"),
            "role": "Admin" if data.get("role") == "Administrator" else data.get("role"),
            "access": data.get("access"),
            "mobile_no": data.get("mobile_no"),
            "email": data.get("email")
        }
        if data.get("password"):
            frappe_data["password"] = data.get("password")
            
        if "assigned_categories" in data:
            frappe_data["assigned_categories"] = [{"rule_category": c} for c in data.get("assigned_categories", [])]
            
        return handle_crud("Staff Master", "update", doc_id=staff_id, data=frappe_data)
    except Exception as e:
        return return_error(str(e), 500)

@frappe.whitelist(allow_guest=True)
def delete_staff(staff_id):
    try:
        return handle_crud("Staff Master", "delete", doc_id=staff_id)
    except Exception as e:
        return return_error(str(e), 500)

# Rule Category CRUD
@frappe.whitelist(allow_guest=True)
def create_rule_category(data):
    try:
        return handle_crud("Rule Category", "create", data=data)
    except Exception as e:
        return return_error(str(e), 500)

@frappe.whitelist(allow_guest=True)
def update_rule_category(category_id, data):
    try:
        return handle_crud("Rule Category", "update", doc_id=category_id, data=data)
    except Exception as e:
        return return_error(str(e), 500)

@frappe.whitelist(allow_guest=True)
def delete_rule_category(category_id):
    try:
        return handle_crud("Rule Category", "delete", doc_id=category_id)
    except Exception as e:
        return return_error(str(e), 500)

# Rule Book CRUD
@frappe.whitelist(allow_guest=True)
def create_rule_book(data):
    try:
        if isinstance(data, str):
            data = json.loads(data)
        
        frappe_data = {
            "rule_category": data.get("rule_category"),
            "rule_book_name": data.get("book_title"),
            "youtube_url": data.get("youtube_url"),
            "audio_file": data.get("audio_url"),
            "rules": [{"rule": r} for r in data.get("rules", [])]
        }
        return handle_crud("Rule Book", "create", data=frappe_data)
    except Exception as e:
        return return_error(str(e), 500)

@frappe.whitelist(allow_guest=True)
def update_rule_book(book_id, data):
    try:
        if isinstance(data, str):
            data = json.loads(data)
            
        frappe_data = {
            "rule_category": data.get("rule_category"),
            "rule_book_name": data.get("book_title"),
            "youtube_url": data.get("youtube_url"),
            "audio_file": data.get("audio_url"),
            "rules": [{"rule": r} for r in data.get("rules", [])]
        }
        return handle_crud("Rule Book", "update", doc_id=book_id, data=frappe_data)
    except Exception as e:
        return return_error(str(e), 500)

@frappe.whitelist(allow_guest=True)
def delete_rule_book(book_id):
    try:
        return handle_crud("Rule Book", "delete", doc_id=book_id)
    except Exception as e:
        return return_error(str(e), 500)
