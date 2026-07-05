# Copyright (c) 2024, maharajan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

class StaffMaster(Document):
	def validate(self):
		if not self.employee_name:
			frappe.throw(_("Employee Name is mandatory"))
		
		if self.user:
			if frappe.db.exists("Staff Master", {"user": self.user, "name": ["!=", self.name]}):
				frappe.throw(_("User must be unique. This User is already assigned to another Staff."))

		if self.mobile_no:
			if frappe.db.exists("Staff Master", {"mobile_no": self.mobile_no, "name": ["!=", self.name]}):
				frappe.throw(_("Mobile number should not duplicate"))

		if self.email:
			if frappe.db.exists("Staff Master", {"email": self.email, "name": ["!=", self.name]}):
				frappe.throw(_("Email should not duplicate"))

