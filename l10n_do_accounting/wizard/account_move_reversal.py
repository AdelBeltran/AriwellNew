from odoo import models, api, fields, _
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)

try:
    from stdnum.do import ncf as ncf_validation
except (ImportError, IOError) as err:
    _logger.debug(err)


class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"

    @api.model
    def _get_refund_type_selection(self):
        selection = [
            ("full_refund", _("Full Refund")),
            ("percentage", _("Percentage")),
            ("fixed_amount", _("Amount")),
        ]

        return selection

    @api.model
    def _get_default_refund_type(self):
        return "full_refund"

    @api.model
    def _get_refund_action_selection(self):

        return [
            ("draft_refund", _("Partial Refund")),
            ("apply_refund", _("Full Refund")),
        ]

    @api.model
    def _default_account(self):
        move_type = self._context.get("type")
        journal = (
            self.env["account.move"]
            .with_context(
                default_type=move_type, default_company_id=self.env.company.id
            )
            ._get_default_journal()
        )
        if move_type in ("out_invoice", "in_refund"):
            return journal.default_credit_account_id.id
        return journal.default_debit_account_id.id

    l10n_latam_country_code = fields.Char(
        related="company_id.l10n_do_country_code",
        help="Technical field used to hide/show fields regarding the localization",
    )
    refund_type = fields.Selection(
        selection=_get_refund_type_selection,
        default=_get_default_refund_type,
    )
    refund_action = fields.Selection(
        selection=_get_refund_action_selection,
        default="draft_refund",
        string="Refund Action",
    )
    percentage = fields.Float()
    amount = fields.Float()
    l10n_do_ecf_modification_code = fields.Selection(
        selection=lambda self: self.env[
            "account.move"
        ]._get_l10n_do_ecf_modification_code(),
        string="e-CF Modification Code",
        copy=False,
    )
    is_ecf_invoice = fields.Boolean(
        string="Is Electronic Invoice",
    )

  
    @api.model
    def default_get(self, fields):
        res = super(AccountMoveReversal, self).default_get(fields)
        move_ids = (
            self.env["account.move"].browse(self.env.context["active_ids"])
            if self.env.context.get("active_model") == "account.move"
            else self.env["account.move"]
        )
        move_ids_use_document = move_ids.filtered(
            lambda move: move.l10n_latam_use_documents
            and move.company_id.l10n_do_country_code == "DO"
        )

        if len(move_ids_use_document) > 1:
            raise UserError(
                _(
                    "You cannot create Credit Notes from multiple "
                    "documents at a time."
                )
            )
        if move_ids_use_document:
            res["is_ecf_invoice"] = move_ids_use_document[0].is_ecf_invoice

        return res




    @api.onchange("refund_type")
    def onchange_refund_type(self):
        if self.refund_type != "full_refund":
            self.refund_method = "refund"

    @api.onchange("refund_action")
    def onchange_refund_action(self):
        if self.refund_action == "apply_refund":
            self.refund_method = "cancel"
        else:
            self.refund_method = "refund"

    def reverse_moves(self):
        active_id = self._context.get("active_id", False)
        if active_id:
            invoice = self.env["account.move"].browse(active_id)
            if self.move_type == "in_invoice":
                ncf = self.l10n_latam_document_number[0:3]
                ncf_digits = len(self.l10n_latam_document_number)
                if (
                    self._context.get("debit_note")
                    and ncf not in ("B03", "E33")
                ):
                    raise UserError(
                        _(
                            "Debit Notes must be type B03 or E33, this NCF "
                            "structure does not comply."
                        )
                    )
                
                elif ncf not in ("B04", "E34"):
                    raise UserError(
                        _(
                            ("Credit Notes must be type B04 or E34, this NCF (Type %s)"
                            " structure does not comply.") % ncf
                        )
                    )

                elif (ncf_digits != 11 and ncf == 'B04') \
                        or (ncf_digits != 13 and ncf == 'E34'):
                    raise UserError(
                        _(
                            ("The number of fiscal sequence in this invoice is "
                            "incorrect, please double check the fiscal sequence")
                            )
                    )

                    # elif (
                    #     invoice.journal_id.l10n_latam_use_documents
                    #     and not ncf_validation.check_dgii(
                    #         invoice.partner_id.vat, self.l10n_latam_document_number)
                    # ):
                    #     raise ValidationError(
                    #         _(
                    #             "NCF rejected by DGII\n\n"
                    #             "NCF *{}* of supplier *{}* was rejected by DGII's "
                    #             "validation service. Please validate if the NCF and "
                    #             "the supplier RNC are type correctly. Otherwhise "
                    #             "your supplier might not have this sequence approved "
                    #             "yet."
                    #         ).format(self.l10n_latam_document_number, invoice.partner_id.name)
                    #     )

        return super(
            AccountMoveReversal,
            self.with_context(
                refund_type=self.refund_type,
                percentage=self.percentage,
                amount=self.amount,
                reason=self.reason,
                l10n_do_ecf_modification_code=self.l10n_do_ecf_modification_code,
            ),
        ).reverse_moves()
