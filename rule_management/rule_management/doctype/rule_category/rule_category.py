# Copyright (c) 2024, maharajan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

class RuleCategory(Document):
	def validate(self):
		if self.category_name:
			if frappe.db.exists("Rule Category", {"category_name": self.category_name, "name": ["!=", self.name]}):
				frappe.throw(_("Category Name should be unique"))
