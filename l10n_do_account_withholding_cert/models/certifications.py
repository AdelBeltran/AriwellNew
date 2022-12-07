# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CertificationTax(models.Model):
    _name = 'certification.tax'

    name = fields.Char('Name')
    norm = fields.Char('Norm')
    report_description = fields.Char('Description on Report')
