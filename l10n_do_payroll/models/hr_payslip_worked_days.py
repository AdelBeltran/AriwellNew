# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HrPayslipWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    last_payslip_vacation = fields.Boolean(string="Nomina de Ultima Vacaciones")