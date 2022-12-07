# -*- coding: utf-8 -*-
from odoo import models, fields

class InheritedAccountJournal(models.Model):
    _inherit = "account.journal"

    statement_import_type = fields.Selection([
        ('bpd', 'Banco Popular'),
        ('bhd', 'Banco BHD Leon'),
        ('res', 'Banreservas'),
        ('manual', 'Sin Formato')
        ], 
        string=u"Formato de Conciliacion del Banco")