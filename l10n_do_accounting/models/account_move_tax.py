from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)


class account_move(models.Model):
    _inherit = "account.move"

    tax_line_ids = fields.One2many('account.move.tax', 'move_id', string='Tax Lines',store=True)

    def _recompute_dynamic_lines(self, recompute_all_taxes=False, recompute_tax_base_amount=False):
        res = super(account_move,self)._recompute_dynamic_lines(recompute_all_taxes,recompute_tax_base_amount)
        for invoice in self:
            invoice.cal_invoice_tax_summary()
        return res

    def cal_invoice_tax_summary(self):
        for invoice in self:
            tax_lst = []
            taxes_grouped = invoice.get_taxes_values()
            invoice.tax_line_ids = False
            for tax in taxes_grouped.values():
                tax_lst.append((0,0,tax))
            invoice.tax_line_ids = tax_lst

    def _prepare_tax_line_vals(self, line, tax):
        vals = {
            'move_id': self.id,
            'name': tax['name'],
            'tax_id': tax['id'],
            'amount': tax['amount'],
            'manual': False,
            'sequence': tax['sequence'],
            'account_analytic_id': tax['analytic'] and line.account_analytic_id.id or False,
            'account_id': tax['account_id'] or tax.get('refund_account_id'),
        }
        return vals

    def tax_get_grouping_key(self, invoice_tax_val):
        """ Returns a string that will be used to group account.invoice.tax sharing the same properties"""
        self.ensure_one()
        return str(invoice_tax_val['tax_id']) + '-' + \
               str(invoice_tax_val['account_id']) + '-' + \
               str(invoice_tax_val['account_analytic_id']) + '-' + \
               str(invoice_tax_val.get('analytic_tag_ids', []))

    def get_taxes_values(self):
        tax_grouped = {}
        round_curr = self.currency_id.round
        for line in self.invoice_line_ids:
            price_reduce = line.price_unit * (1.0 - line.discount / 100.0)
            taxes = line.tax_ids._origin.compute_all(price_reduce, quantity=line.quantity, product=line.product_id, partner=line.partner_id)['taxes']
            for tax in taxes:
                val = self._prepare_tax_line_vals(line, tax)
                key = self.tax_get_grouping_key(val)
                if key not in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['amount'] += val['amount']
        return tax_grouped


class account_move_tax(models.Model):
    _name = "account.move.tax"
    _description = "Invoice Tax"

    move_id = fields.Many2one('account.move', string='Account Move')
    name = fields.Char(string='Tax Description', required=True)
    tax_id = fields.Many2one('account.tax', string='Tax')
    amount = fields.Monetary()
    amount_rounding = fields.Monetary()
    amount_total = fields.Monetary(string="Amount Total", compute='_compute_amount_total')
    manual = fields.Boolean(default=True)
    sequence = fields.Integer(help="Gives the sequence order when displaying a list of invoice tax.")
    company_id = fields.Many2one('res.company', string='Company', related='move_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', related='move_id.currency_id', store=True, readonly=True)
    account_id = fields.Many2one('account.account', string='Tax Account', domain=[('deprecated', '=', False)])
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic account')

    @api.depends('amount', 'amount_rounding')
    def _compute_amount_total(self):
        for tax_line in self:
            tax_line.amount_total = tax_line.amount + tax_line.amount_rounding