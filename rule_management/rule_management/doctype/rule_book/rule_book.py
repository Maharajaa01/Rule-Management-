# Copyright (c) 2024, maharajan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

class RuleBook(Document):
	def validate(self):
		if not self.rule_book_name:
			frappe.throw(_("Rule Book Name is mandatory"))
		if not self.rule_category:
			frappe.throw(_("Rule Category is mandatory"))
		if not self.get("rules") or len(self.get("rules")) == 0:
			frappe.throw(_("At least one rule must exist before saving"))
