from werkzeug import urls

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError, AccessError
# import logging
# _logger = logging.getLogger(__name__)

# try:
#     from stdnum.do import ncf as ncf_validation, rnc

# except (ImportError, IOError) as err:
#     _logger.debug(err)


ncf_dict = {
    "B01": "fiscal",
    "B02": "consumo",
    "B15": "gov",
    "B14": "especial",
    "B12": "unico",
    "B16": "export",
    "B03": "debit",
    "B04": "credit",
    "B13": "minor",
    "B11": "informal",
    "B17": "exterior",
    "E31" : "e-fiscal",
    "E32" : "e-consumer",
    "E33" : "e-debit_note",
    "E34" : "e-credit_note",
    "E41" : "e-informal",
    "E43" : "e-minor",
    "E44" : "e-special",
    "E45" : "e-governmental",
    "E46" : "e-export",
    "E47" : "e-exterior",
}

class AccountMove(models.Model):
    _inherit = "account.move"

    @property
    def _sequence_fixed_regex(self):
        if self.l10n_latam_country_code == "DO" and self.l10n_latam_use_documents:
            return r'^(?P<prefix1>.*?)(?P<seq>\d{0,9})(?P<suffix>\D*?)$'
        return super(AccountMove, self)._sequence_fixed_regex



    def _get_l10n_do_cancellation_type(self):
        """ Return the list of cancellation types required by DGII. """
        return [
            ("01", _("01 - Pre-printed Invoice Impairment")),
            ("02", _("02 - Printing Errors (Pre-printed Invoice)")),
            ("03", _("03 - Defective Printing")),
            ("04", _("04 - Correction of Product Information")),
            ("05", _("05 - Product Change")),
            ("06", _("06 - Product Return")),
            ("07", _("07 - Product Omission")),
            ("08", _("08 - NCF Sequence Errors")),
            ("09", _("09 - For Cessation of Operations")),
            ("10", _("10 - Lossing or Hurting Of Counterfoil")),
        ]

    def _get_l10n_do_ecf_modification_code(self):
        """ Return the list of e-CF modification codes required by DGII. """
        return [
            ("1", _("01 - Total Cancellation")),
            ("2", _("02 - Text Correction")),
            ("3", _("03 - Amount correction")),
            ("4", _("04 - NCF replacement issued in contingency")),
            ("5", _("05 - Reference Electronic Consumer Invoice")),
        ]

    def _get_l10n_do_income_type(self):
        """ Return the list of income types required by DGII. """
        return [
            ("01", _("01 - Operational Incomes")),
            ("02", _("02 - Financial Incomes")),
            ("03", _("03 - Extraordinary Incomes")),
            ("04", _("04 - Leasing Incomes")),
            ("05", _("05 - Income for Selling Depreciable Assets")),
            ("06", _("06 - Other Incomes")),
        ]

    l10n_do_expense_type = fields.Selection(
        selection=lambda self: self.env["res.partner"]._get_l10n_do_expense_type(),
        string="Cost & Expense Type",
    )

    l10n_do_cancellation_type = fields.Selection(
        selection="_get_l10n_do_cancellation_type",
        string="Cancellation Type",
        copy=False,
    )

    l10n_do_income_type = fields.Selection(
        selection="_get_l10n_do_income_type",
        string="Income Type",
        copy=False,
        default=lambda self: self._context.get("l10n_do_income_type", "01"),
    )

    l10n_do_origin_ncf = fields.Char(
        string="Modifies",
    )

    is_ecf_invoice = fields.Boolean(
        copy=False,
        default=lambda self: self.env.user.company_id.l10n_do_ecf_issuer
        and self.env.user.company_id.l10n_do_country_code
        and self.env.user.company_id.l10n_do_country_code == "DO",
    )
    l10n_do_ecf_modification_code = fields.Selection(
        selection="_get_l10n_do_ecf_modification_code",
        string="e-CF Modification Code",
        copy=False,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    l10n_do_ecf_security_code = fields.Char(string="e-CF Security Code", copy=False)
    l10n_do_ecf_sign_date = fields.Datetime(string="e-CF Sign Date", copy=False)
    l10n_do_electronic_stamp = fields.Char(
        string="Electronic Stamp",
        compute="_compute_l10n_do_electronic_stamp",
        store=True,
    )
    l10n_do_company_in_contingency = fields.Boolean(
        string="Company in contingency",
        compute="_compute_company_in_contingency",
    )
    l10n_latam_country_code = fields.Char(
        "Country Code",
        related="company_id.country_id.code",
    )

    l10n_do_fiscal_sequence_id = fields.Many2one(
        "account.fiscal.sequence", string="Fiscal Sequence",
        copy=False, compute="_compute_l10n_do_fiscal_sequence", store=True,
    )

    l10n_do_ncf_expiration_date = fields.Date(
        string="Valid until",
    )

    l10n_do_fiscal_sequence_status = fields.Selection(
        [
            ("no_fiscal", "No fiscal"),
            ("fiscal_ok", "Ok"),
            ("almost_no_sequence", "Almost no sequence"),
            ("no_sequence", "Depleted"),
        ],
        compute="_compute_l10n_do_fiscal_sequence_status",
    )


    @api.depends("company_id", "company_id.l10n_do_ecf_issuer")
    def _compute_company_in_contingency(self):
        for invoice in self:
            ecf_invoices = self.search([("is_ecf_invoice", "=", True)], limit=1)
            invoice.l10n_do_company_in_contingency = bool(
                ecf_invoices and not invoice.company_id.l10n_do_ecf_issuer
            )

    @api.depends("l10n_do_ecf_security_code", "l10n_do_ecf_sign_date", "invoice_date")
    @api.depends_context("l10n_do_ecf_service_env")
    def _compute_l10n_do_electronic_stamp(self):

        for invoice in self.filtered(
            lambda i: i.is_ecf_invoice
            and i.l10n_do_ecf_security_code
            and i.l10n_do_ecf_sign_date
        ):

            ecf_service_env = self.env.context.get("l10n_do_ecf_service_env", "CerteCF")
            doc_code_prefix = invoice.l10n_latam_document_type_id.doc_code_prefix
            has_sign_date = doc_code_prefix != "E32" or (
                doc_code_prefix == "E32" and invoice.amount_total_signed >= 250000
            )

            qr_string = "https://ecf.dgii.gov.do/%s/ConsultaTimbre?" % ecf_service_env
            qr_string += "RncEmisor=%s&" % invoice.company_id.vat or ""
            qr_string += (
                "RncComprador=%s&" % invoice.commercial_partner_id.vat
                if invoice.l10n_latam_document_type_id.doc_code_prefix[1:] != "43"
                else invoice.company_id.vat
            )
            qr_string += "ENCF=%s&" % invoice.ref or ""
            qr_string += "FechaEmision=%s&" % (
                invoice.invoice_date or fields.Date.today()
            ).strftime("%d-%m-%Y")
            qr_string += "MontoTotal=%s&" % (
                "%f" % abs(invoice.amount_total_signed)
            ).rstrip("0").rstrip(".")

            # DGII doesn't want FechaFirma if Consumo Electronico and < 250K
            # ¯\_(ツ)_/¯
            if has_sign_date:
                qr_string += (
                    "FechaFirma=%s&"
                    % fields.Datetime.context_timestamp(
                        self.with_context(tz="America/Santo_Domingo"),
                        invoice.l10n_do_ecf_sign_date,
                    ).strftime("%d-%m-%Y %H:%M:%S")
                )

            qr_string += "CodigoSeguridad=%s" % invoice.l10n_do_ecf_security_code or ""

            invoice.l10n_do_electronic_stamp = urls.url_quote_plus(qr_string)

    def button_cancel(self):

        fiscal_invoice = self.filtered(
            lambda inv: inv.l10n_latam_country_code == "DO"
            and self.move_type[-6:] in ("nvoice", "refund")
            and inv.l10n_latam_use_documents
        )

        if len(fiscal_invoice) > 1:
            raise ValidationError(
                _("You cannot cancel multiple fiscal invoices at a time.")
            )

        if fiscal_invoice and not self.env.user.has_group(
            "l10n_do_accounting.group_l10n_do_fiscal_invoice_cancel"
        ):
            raise AccessError(_("You are not allowed to cancel Fiscal Invoices"))


        if fiscal_invoice:
            action = self.env.ref(
                "l10n_do_accounting.action_account_move_cancel"
            ).read()[0]
            action["context"] = {"default_move_id": fiscal_invoice.id}
            return action

        return super(AccountMove, self).button_cancel()

    def action_reverse(self):

        fiscal_invoice = self.filtered(
            lambda inv: inv.l10n_latam_country_code == "DO"
            and self.move_type[-6:] in ("nvoice", "refund")
        )
        if fiscal_invoice and not self.env.user.has_group(
            "l10n_do_accounting.group_l10n_do_fiscal_credit_note"
        ):
            raise AccessError(_("You are not allowed to issue Fiscal Credit Notes"))

        return super(AccountMove, self).action_reverse()


    def _get_l10n_latam_documents_domain(self):
        for p in self:
            if not p.partner_id.l10n_do_dgii_tax_payer_type:
                raise ValidationError(
                    _(
                        "A Type Of Taxpayers is Mandatory. "
                        "Please set the current Type of this contact"
                    )
                )

        self.ensure_one()
        domain = super()._get_l10n_latam_documents_domain()
        if (
            self.journal_id.l10n_latam_use_documents
            and self.journal_id.company_id.country_id == self.env.ref("base.do")
        ):
            if self.partner_id == self.company_id.partner_id:
                ncf_types = ['minor','import']
            else:
                ncf_types = self.journal_id._get_journal_ncf_types(
                    counterpart_partner=self.partner_id.commercial_partner_id, invoice=self
                )
            domain += [
                "|",
                ("l10n_do_ncf_type", "=", False),
                ("l10n_do_ncf_type", "in", ncf_types),
            ]
            codes = self.journal_id._get_journal_codes()
            if codes:
                domain.append(("code", "in", codes))
        return domain



    @api.constrains("move_type", "l10n_latam_document_type_id")
    def _check_invoice_type_document_type(self):
        super()._check_invoice_type_document_type()
        for rec in self.filtered(
            lambda r: r.company_id.country_id == self.env.ref("base.do")
            and r.l10n_latam_document_type_id
        ):
            partner_vat = rec.partner_id.vat
            l10n_latam_document_type = rec.l10n_latam_document_type_id
            if not partner_vat and l10n_latam_document_type.is_vat_required:
                raise ValidationError(
                    _(
                        "A VAT is mandatory for this type of NCF. "
                        "Please set the current VAT of this client"
                    )
                )

            elif rec.move_type in ("out_invoice", "out_refund"):
                if (
                    rec.amount_untaxed_signed >= 250000
                    and l10n_latam_document_type.l10n_do_ncf_type[-7:] != "special"
                    and not rec.partner_id.vat
                ):
                    raise UserError(
                        _(
                            "If the invoice amount is greater than RD$250,000.00 "
                            "the customer should have a VAT to validate the invoice"
                        )
                    )
            # DGII SERVER DOWN
            # elif (
            #         l10n_latam_document_type.l10n_do_ncf_type[-7:] == "nformal"
            # ):
            #     result = rnc.check_dgii(partner_vat)
            #     if result is not None:
            #         raise UserError(
            #             _(
            #                 "This Contact is registred on *DGII* Plataform\n"
            #                 "Ensure to ask for a Fiscal Invoice Number"
            #             )
            #         )


    @api.constrains("l10n_latam_document_type_id")
    def _onchange_l10n_latam_document_type(self):
        for rec in self.filtered(
            lambda r:  r.company_id.country_id == self.env.ref("base.do")
            and r.move_type == "in_invoice"
            and r.l10n_latam_document_type_id.l10n_do_ncf_type in (
                 "minor",
                "e-minor"
            )
        ):
            rec.partner_id = rec.company_id.partner_id




    # @api.onchange("l10n_latam_document_number", "l10n_do_origin_ncf")
    # def _onchange_l10n_latam_document_number(self):
    #     for rec in self.filtered(
    #         lambda r: r.company_id.country_id == self.env.ref("base.do")
    #         and r.l10n_latam_document_type_id.l10n_do_ncf_type is not False
    #         and r.journal_id.l10n_latam_use_documents
    #         and r.l10n_latam_document_number
    #         and r.move_type == "in_invoice"
    #     ):

    #         NCF = rec.l10n_latam_document_number if rec.l10n_latam_document_number else None
    #         if not ncf_validation.is_valid(NCF):
    #             raise UserError(_(
    #                 "NCF mal digitado\n\n"
    #                 "El comprobante *{}* no tiene la estructura correcta "
    #                 "valide si lo ha digitado correctamente")
    #                 .format(NCF))

    #         if NCF[-10:-8] == '02' or NCF[1:3] == '32':
    #             raise ValidationError(_(
    #                 "NCF *{}* NO corresponde con el tipo de documento\n\n"
    #                 "No puede registrar Comprobantes Consumidor Final (02)")
    #                 .format(NCF))

    #         elif (
    #             not ncf_validation.check_dgii(self.partner_id.vat, NCF)
    #             and ncf_validation.is_valid(NCF)
    #             and len(NCF) == 11
    #         ):
    #             raise ValidationError(_(
    #                 u"NCF NO pasó validación en DGII\n\n"
    #                 u"¡El número de comprobante *{}* del proveedor "
    #                 u"*{}* no pasó la validación en "
    #                 "DGII! Verifique que el NCF y el RNC del "
    #                 u"proveedor estén correctamente "
    #                 u"digitados, o si los números de ese NCF se "
    #                 "le agotaron al proveedor")
    #                 .format(NCF, self.partner_id.name))


    @api.onchange("partner_id")
    def _onchange_partner_id(self):

        if (
            self.company_id.country_id == self.env.ref("base.do")
            and self.l10n_latam_document_type_id
            and self.move_type == "in_invoice"
            and self.partner_id
        ):
            self.l10n_do_expense_type = (
                self.partner_id.l10n_do_expense_type
                if not self.l10n_do_expense_type
                else self.l10n_do_expense_type
            )

        return super(AccountMove, self)._onchange_partner_id()

    def _reverse_move_vals(self, default_values, cancel=True):

        ctx = self.env.context
        amount = ctx.get("amount")
        percentage = ctx.get("percentage")
        refund_type = ctx.get("refund_type")
        reason = ctx.get("reason")
        l10n_do_ecf_modification_code = ctx.get("l10n_do_ecf_modification_code")

        res = super(AccountMove, self)._reverse_move_vals(
            default_values=default_values, cancel=cancel
        )

        if self.l10n_latam_country_code == "DO":
            res["l10n_do_origin_ncf"] = self.l10n_latam_document_number
            res["l10n_do_ecf_modification_code"] = l10n_do_ecf_modification_code

        if refund_type in ("percentage", "fixed_amount"):
            price_unit = (
                amount
                if refund_type == "fixed_amount"
                else self.amount_untaxed * (percentage / 100)
            )
            res["line_ids"] = False
            res["invoice_line_ids"] = [
                (0, 0, {"name": reason or _("Refund"), "price_unit": price_unit})
            ]
        return res

    @api.constrains("name", "partner_id", "company_id")
    def _check_unique_vendor_number(self):

        l10n_do_invoice = self.filtered(
            lambda inv: inv.l10n_latam_country_code == "DO"
            and inv.l10n_latam_use_documents
            and inv.is_purchase_document()
            and inv.l10n_latam_document_number
        )

        for rec in l10n_do_invoice:
            domain = [
                ("move_type", "=", rec.move_type),
                ("l10n_latam_document_number", "=", rec.l10n_latam_document_number),
                ("company_id", "=", rec.company_id.id),
                ("id", "!=", rec.id),
                ("commercial_partner_id", "=", rec.commercial_partner_id.id),
            ]
            if rec.search(domain):
                raise ValidationError(
                    _("Vendor bill NCF must be unique per vendor and company.")
                )
    def _is_manual_document_number(self, journal):

        if (
            self.company_id.country_id == self.env.ref("base.do")
            and self.l10n_latam_document_type_id
        ):
            return self.move_type in (
                "in_invoice",
                "in_refund",
            ) and self.l10n_latam_document_type_id.l10n_do_ncf_type not in (
                "minor",
                "e-minor",
                "informal",
                "e-informal",
            )

        return super(AccountMove, self)._is_manual_document_number(journal=journal)

    def _get_name_invoice_report(self):
        self.ensure_one()
        if self.l10n_latam_use_documents and self.l10n_latam_country_code == "DO":
            return "l10n_do_accounting.report_invoice_document_inherited"
        return super()._get_name_invoice_report()


    @api.depends(
        "journal_id",
        "l10n_latam_use_documents",
        "state",
        "l10n_latam_document_type_id",
        "invoice_date", "move_type",
    )
    def _compute_l10n_do_fiscal_sequence(self):
        """ Compute the sequence and fiscal position to be used depending on
            the fiscal type that has been set on the invoice (or partner).
        """
        # for inv in self.filtered(lambda i: i.state == "draft"):
        # for inv in self.filtered(lambda i: i.state == "draft"):
        for inv in self:
            assing_document_number = False
            if (
                inv.move_type in ("out_invoice", "out_refund")
            ):
                assing_document_number = True

            if (
                inv.move_type == "in_invoice"
                and inv.l10n_latam_document_type_id.l10n_do_ncf_type in ("minor", "e-minor")
                and inv.partner_id == inv.company_id.partner_id
            ):
                assing_document_number = True

            if (
                inv.move_type == "in_invoice"
                and inv.l10n_latam_document_type_id.l10n_do_ncf_type in (
                "informal",
                "e-informal",
                )
                and len(inv.partner_id.vat) == 11
            ):
                assing_document_number = True


            if inv.l10n_latam_use_documents and assing_document_number:

                domain = [
                    ("company_id", "=", inv.company_id.id),
                    ("fiscal_type_id", "=", inv.l10n_latam_document_type_id.id),
                    ("state", "=", "active"),
                ]
                if inv.invoice_date:
                    domain.append(("expiration_date", ">=", inv.invoice_date))
                else:
                    today = fields.Date.context_today(inv)
                    domain.append(("expiration_date", ">=", today))

                l10n_do_fiscal_sequence_id = inv.env["account.fiscal.sequence"].search(
                    domain, order="expiration_date, id desc"
                )

                if not l10n_do_fiscal_sequence_id:
                    pass
                elif l10n_do_fiscal_sequence_id.state == "active":

                    inv.l10n_do_fiscal_sequence_id = l10n_do_fiscal_sequence_id
                else:
                    l10n_do_fiscal_sequence_id = False
            else:
                l10n_do_fiscal_sequence_id = False

    @api.depends(
        "l10n_do_fiscal_sequence_id",
        "l10n_do_fiscal_sequence_id.sequence_remaining",
        "l10n_do_fiscal_sequence_id.remaining_percentage",
        "state",
        "journal_id",
    )
    def _compute_l10n_do_fiscal_sequence_status(self):
        """ Identify the percentage fiscal sequences that has been used so far.
            With this result the user can be warned if it's above the threshold
            or if there's no more sequences available.
        """
        for inv in self:

            if not inv.l10n_latam_use_documents or not inv.l10n_do_fiscal_sequence_id:
                inv.l10n_do_fiscal_sequence_status = "no_fiscal"
            else:
                fs_id = inv.l10n_do_fiscal_sequence_id  # Fiscal Sequence
                remaining = fs_id.sequence_remaining
                remaining_percent = fs_id.remaining_percentage
                seq_length = fs_id.sequence_end - fs_id.sequence_start + 1

                consumed_percent = round(1 - (remaining / seq_length), 2) * 100

                if consumed_percent < remaining_percent:
                    inv.l10n_do_fiscal_sequence_status = "fiscal_ok"
                elif remaining > 0 and consumed_percent >= remaining_percent:
                    inv.l10n_do_fiscal_sequence_status = "almost_no_sequence"
                else:
                    inv.l10n_do_fiscal_sequence_status = "no_sequence"

    @api.constrains("state", "invoice_line_ids", "partner_id")
    def validate_products_export_ncf(self):
        """ Validates that an invoices with a partner from country != DO
            and products type != service must have Exportaciones NCF.
            See DGII Norma 05-19, Art 10 for further information.
        """
        for inv in self:
            if (
                inv.move_type == "out_invoice"
                and inv.state in ("posted", "cancel")
                and inv.partner_id.country_id
                and inv.partner_id.country_id.code != "DO"
                and inv.l10n_latam_use_documents
            ):
                if any([p for p in inv.invoice_line_ids.mapped("product_id") if p.type != "service"]):
                    if (
                        ncf_dict.get(inv.l10n_latam_document_type_id.doc_code_prefix) in (
                            "exterior", "e-exterior")
                    ):
                        raise UserError(_("Goods sales to overseas customers must have " "Exportaciones Fiscal Type"))
                elif (
                    ncf_dict.get(inv.l10n_latam_document_type_id.doc_code_prefix) in ("consumo", "e-consumer")
                ):
                    raise UserError(_("Service sales to oversas customer must have " "Consumo Fiscal Type"))

    @api.constrains("state", "tax_line_ids")
    def validate_informal_withholding(self):
        """ Validates an invoice with Comprobante de Compras has 100% ITBIS
            withholding.
            See DGII Norma 05-19, Art 7 for further information.
        """
        for inv in self.filtered(lambda i: i.move_type == "in_invoice" and i.state == "posted"):
            if (
                (
                    ncf_dict.get(inv.l10n_latam_document_type_id.doc_code_prefix) in ("informal","e-informal")
                )
                and inv.l10n_latam_use_documents
            ):
                # If the sum of all taxes of category ITBIS is not 0
                if sum(
                    [
                        tax.amount
                        for tax in inv.tax_line_ids.mapped("tax_id").filtered(lambda t: t.purchase_tax_type in ['itbis','ritbis'])
                    ]
                ):
                    raise UserError(_("You must withhold 100% of ITBIS"))


    @api.constrains('state', 'tax_line_ids')
    def validate_special_exempt(self):
        """ Validates an invoice with Regímenes Especiales sale_fiscal_type
            does not contain nor ITBIS or ISC.
            See DGII Norma 05-19, Art 3 for further information.
        """
        for inv in self:
            if inv.l10n_latam_use_documents:
                if (
                    inv.move_type == 'out_invoice'
                    and inv.state in ('posted', 'cancel')
                    and inv.l10n_latam_document_type_id.l10n_do_ncf_type
                    and 'special' in inv.l10n_latam_document_type_id.l10n_do_ncf_type
                ):

                    # If any invoice tax in ITBIS or ISC
                    if any([
                            tax for tax in inv.tax_line_ids.mapped('tax_id')
                            .filtered(lambda tax: tax.tax_group_id.name in (
                                'ITBIS', 'ISC') and tax.amount != 0)
                    ]):
                        raise UserError(_(
                            "No puede validar una factura para Regímen Especial "
                            " con ITBIS/ISC.\n\n"
                            "Consulte Norma General 05-19, Art. 3 de la DGII")
                        )



    def _post(self, soft=True):
        """ After all invoice validation routine, consume a NCF sequence and
            write it into ref field.
        """
        res = super()._post(soft)
        for inv in self.filtered(lambda i: i.state == "draft"):
            non_payer_type_invoices = self.filtered(
                lambda i: i.company_id.country_id == self.env.ref("base.do")
                and i.l10n_latam_use_documents
                and not i.partner_id.l10n_do_dgii_tax_payer_type
             )


            if non_payer_type_invoices:
                raise ValidationError(_("Fiscal invoices require partner fiscal type"))

            # if inv.amount_total == 0:
            #     raise UserError(_(u"You cannot validate an invoice whose " u"total amount is equal to 0"))

            if inv.l10n_latam_use_documents:

                # Because a Fiscal Sequence can be depleted while an invoice
                # is waiting to be validated, compute fiscal_sequence_id again
                # on invoice validate.
                inv._compute_l10n_do_fiscal_sequence()
                if not inv.l10n_latam_document_number and not inv.l10n_do_fiscal_sequence_id:
                    raise ValidationError(_(
                                            "There is not active Sequence for "
                                            "{}"
                                            ).format(self.l10n_latam_document_type_id.name))



        for inv in self:
            if inv.l10n_latam_use_documents and not inv.l10n_latam_document_number and res and inv.l10n_do_fiscal_sequence_id:
                document_number = inv.l10n_do_fiscal_sequence_id.get_fiscal_number()
                inv.state = "draft"
                inv.write(
                    {
                        "state": "posted",
                        "l10n_latam_document_number": document_number,
                        "l10n_do_ncf_expiration_date": inv.l10n_do_fiscal_sequence_id.expiration_date,
                        "payment_reference" : '%s - %s' % (inv.name, document_number)
                    }
                )

                self._onchange_payment_reference()

        return res
