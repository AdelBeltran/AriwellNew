# -*- coding: utf-8 -*-
import json
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # need_certification = fields.Boolean(compute="_compute_need_certification")
    need_certification = fields.Boolean(default=False)

    certification_check = fields.Boolean(default=False, string="Certificación")


    # def _get_certification_in_payments(self, payment, certifications):
    #     payment_id = self.env['account.payment'].browse(payment.get('account_payment_id'))
    #     move_id = self.env['account.move'].browse(payment.get('move_id'))
    #     for move_line in move_id.line_ids: #payment_id.move_line_ids:
    #         certification = move_line.account_id.certification_id
    #         if certification:
    #             certifications.setdefault(certification, 0)
    #             certifications[certification] += move_line.credit

    #     return certifications

    def get_certification_data(self):
        # self.date_format_long()
        # payments = self._get_invoice_payment_widget()
        


        # certifications = {}
        # for line in self.line_ids.filtered(lambda l: l.account_id.certification_id):
        #     certification = line.account_id.certification_id
        #     certifications.setdefault(certification, 0)
        #     certifications[certification] += line.credit

        # for payment in payments:
        #     certifications = self._get_certification_in_payments(payment, certifications)

        # return certifications
        return True

    @api.depends('payment_state')
    def _compute_need_certification(self):
        for invoice in self:
            need_certification = False #False
            invoice.need_certification = need_certification

            if invoice.payment_state in ['in_payment', 'paid']:
                for line in invoice.line_ids.filtered(lambda l: l.account_id.certification_id):
                    _logger.debug("Debug message "+line +" end")
                    need_certification = True
                    if need_certification:
                        invoice.need_certification = True
                        break

                if need_certification:
                    continue

                for payment in invoice._get_invoice_payment_widget():
                    need_certification = self._get_certification_in_payments(payment, {})
                    if need_certification:
                        invoice.need_certification = True
                        break

                invoice.need_certification = need_certification

    def date_format_long(self, date=fields.Date.today()):
        terms = {
            'January': 'Enero',
            'February': 'Febrero',
            'March': 'Marzo',
            'April': 'Abril',
            'May': 'Mayo',
            'June': 'Junio',
            'July': 'Julio',
            'August': 'Agosto',
            'September': 'Septiembre',
            'October': 'Octubre',
            'November': 'Noviembre',
            'December': 'Diciembre',
            'Monday': 'lunes',
            'Tuesday': 'martes',
            'Wednesday':'miércoles',
            'Thursday':'jueves',
            'Friday':'viernes',
            'Saturday':'sábado',
            'Sunday':'domingo',
        }

        str_month = terms.get(date.strftime('%B'))
        str_day = terms.get(date.strftime('%A'))
        day = date.strftime('%d')
        year = date.strftime('%Y')
        date.strftime('%A, %d de %B del %Y')
        return '{} de {} del {}'.format(day, str_month, year)

    def print_certification(self):
        return self.env.ref('l10n_do_account_withholding_cert.certification_report').report_action(self)


class AccountAccount(models.Model):
    _inherit = 'account.account'

    certification_id = fields.Many2one('certification.tax', string='Para Certificacion')


