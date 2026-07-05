import os
import json

base_dir = "/home/maharajan/Dont-quit/apps/rule_management/rule_management/rule_management/doctype"

doctypes = [
    {
        "name": "Staff Category",
        "is_submittable": 0,
        "istable": 0,
        "custom": 0,
        "module": "Rule Management",
        "fields": [
            {"fieldname": "category_name", "fieldtype": "Data", "label": "Category Name", "reqd": 1},
            {"fieldname": "icon", "fieldtype": "Data", "label": "Icon"},
            {"fieldname": "description", "fieldtype": "Small Text", "label": "Description"},
            {"fieldname": "is_active", "fieldtype": "Check", "label": "Is Active", "default": "1"}
        ]
    },
    {
        "name": "Assigned Rule Category",
        "istable": 1,
        "custom": 0,
        "module": "Rule Management",
        "fields": [
            {"fieldname": "rule_category", "fieldtype": "Link", "label": "Rule Category", "options": "Rule Category", "in_list_view": 1}
        ]
    },
    {
        "name": "Staff Master",
        "istable": 0,
        "custom": 0,
        "module": "Rule Management",
        "fields": [
            {"fieldname": "employee_name", "fieldtype": "Data", "label": "Employee Name", "reqd": 1},
            {"fieldname": "mobile_no", "fieldtype": "Data", "label": "Mobile No", "unique": 1},
            {"fieldname": "email", "fieldtype": "Data", "label": "Email", "unique": 1},
            {"fieldname": "user", "fieldtype": "Link", "label": "User", "options": "User", "unique": 1},
            {"fieldname": "staff_category", "fieldtype": "Link", "label": "Staff Category", "options": "Staff Category"},
            {"fieldname": "status", "fieldtype": "Select", "label": "Status", "options": "Active\nInactive", "default": "Active"},
            {"fieldname": "assigned_categories", "fieldtype": "Table", "label": "Assigned Categories", "options": "Assigned Rule Category"}
        ]
    },
    {
        "name": "Rule Category",
        "istable": 0,
        "custom": 0,
        "module": "Rule Management",
        "fields": [
            {"fieldname": "category_name", "fieldtype": "Data", "label": "Category Name", "reqd": 1, "unique": 1},
            {"fieldname": "icon", "fieldtype": "Data", "label": "Icon"},
            {"fieldname": "description", "fieldtype": "Small Text", "label": "Description"},
            {"fieldname": "is_active", "fieldtype": "Check", "label": "Is Active", "default": "1"}
        ]
    },
    {
        "name": "Rule List",
        "istable": 1,
        "custom": 0,
        "module": "Rule Management",
        "fields": [
            {"fieldname": "idx_no", "fieldtype": "Int", "label": "Idx No"},
            {"fieldname": "rule", "fieldtype": "Small Text", "label": "Rule", "reqd": 1, "in_list_view": 1}
        ]
    },
    {
        "name": "Rule Book",
        "istable": 0,
        "custom": 0,
        "module": "Rule Management",
        "fields": [
            {"fieldname": "rule_book_name", "fieldtype": "Data", "label": "Rule Book Name", "reqd": 1},
            {"fieldname": "rule_category", "fieldtype": "Link", "label": "Rule Category", "options": "Rule Category", "reqd": 1},
            {"fieldname": "icon", "fieldtype": "Data", "label": "Icon"},
            {"fieldname": "youtube_url", "fieldtype": "Data", "label": "YouTube URL"},
            {"fieldname": "audio_file", "fieldtype": "Attach", "label": "Audio File"},
            {"fieldname": "description", "fieldtype": "Small Text", "label": "Description"},
            {"fieldname": "is_active", "fieldtype": "Check", "label": "Is Active", "default": "1"},
            {"fieldname": "rules", "fieldtype": "Table", "label": "Rules", "options": "Rule List"}
        ]
    }
]

# Set permissions
# Administrator: Full CRUD on all non-table Doctypes
# Staff: Read on Rule Category, Rule Book, Own Staff Master. No delete.

for dt in doctypes:
    name_snake = dt['name'].lower().replace(" ", "_")
    dir_path = os.path.join(base_dir, name_snake)
    os.makedirs(dir_path, exist_ok=True)
    
    # Generate JSON
    dt_json = {
        "actions": [],
        "creation": "2024-01-01 00:00:00.000000",
        "doctype": "DocType",
        "engine": "InnoDB",
        "field_order": [f["fieldname"] for f in dt["fields"]],
        "fields": dt["fields"],
        "links": [],
        "modified": "2024-01-01 00:00:00.000000",
        "modified_by": "Administrator",
        "module": "Rule Management",
        "name": dt["name"],
        "owner": "Administrator",
        "permissions": [],
        "sort_field": "modified",
        "sort_order": "DESC",
        "states": [],
        "custom": 0,
        "istable": dt.get("istable", 0),
        "is_submittable": dt.get("is_submittable", 0)
    }

    if dt["istable"] == 0:
        if dt["name"] in ["Staff Category"]:
            dt_json["permissions"] = [
                {"role": "Administrator", "read": 1, "write": 1, "create": 1, "delete": 1}
            ]
        elif dt["name"] == "Staff Master":
            dt_json["permissions"] = [
                {"role": "Administrator", "read": 1, "write": 1, "create": 1, "delete": 1},
                {"role": "Staff", "read": 1, "write": 0, "create": 0, "delete": 0, "if_owner": 1} # Own Staff Master
            ]
        elif dt["name"] in ["Rule Category", "Rule Book"]:
            dt_json["permissions"] = [
                {"role": "Administrator", "read": 1, "write": 1, "create": 1, "delete": 1},
                {"role": "Staff", "read": 1, "write": 0, "create": 0, "delete": 0}
            ]

    # Write JSON
    with open(os.path.join(dir_path, f"{name_snake}.json"), "w") as f:
        json.dump(dt_json, f, indent=1)

    # Write Python
    py_content = f"""# Copyright (c) 2024, maharajan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class {dt['name'].replace(' ', '')}(Document):
\tpass
"""
    with open(os.path.join(dir_path, f"{name_snake}.py"), "w") as f:
        f.write(py_content)

print("Done generating JSON and PY files.")
