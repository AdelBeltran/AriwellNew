from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    purchase_journal_id = fields.Many2one('account.journal',
                                          company_dependent=True,
                                          domain=[('type', '=', 'purchase')])
