import json
with open("/home/maharajan/Dont-quit/apps/rule_management/rule_management/rule_management/doctype/staff_master/staff_master.json", "r") as f:
    data = json.load(f)

data["fields"].insert(4, {"fieldname": "login_id", "fieldtype": "Data", "label": "Login ID", "unique": 1, "reqd": 1})
data["fields"].insert(5, {"fieldname": "password", "fieldtype": "Password", "label": "Password", "reqd": 1})

with open("/home/maharajan/Dont-quit/apps/rule_management/rule_management/rule_management/doctype/staff_master/staff_master.json", "w") as f:
    json.dump(data, f, indent=1)
