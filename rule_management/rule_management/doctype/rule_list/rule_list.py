# Copyright (c) 2024, maharajan and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

class RuleList(Document):
	def validate(self):
		if not self.rule:
			frappe.throw(_("Rule cannot be empty"))
