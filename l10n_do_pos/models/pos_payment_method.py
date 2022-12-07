from odoo import models, fields, api


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    def _get_l10n_do_payment_form(self):
        return self.env['account.journal'].sudo()._get_l10n_do_payment_form()

    l10n_do_payment_form = fields.Selection(
        selection="_get_l10n_do_payment_form",
        string="Forma de Pago",
    )

    @api.onchange('cash_journal_id')
    def change_cash_journal_id(self):
        self.l10n_do_payment_form = self.cash_journal_id.l10n_do_payment_form
