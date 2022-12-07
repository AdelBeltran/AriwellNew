import json
import re

import lxml.html
import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError

try:
    from stdnum.do import rnc, cedula
except (ImportError, IOError) as err:
    _logger.debug(str(err))

class Partner(models.Model):
    _inherit = "res.partner"


    def _get_l10n_do_dgii_payer_types_selection(self):
        """Return the list of payer types needed in invoices to clasify accordingly to
        DGII requirements."""
        return [
            ("taxpayer", _("Fiscal Tax Payer")),
            ("non_payer", _("Non Tax Payer")),
            ("nonprofit", _("Nonprofit Organization")),
            ("special", _("special from Tax Paying")),
            ("governmental", _("Governmental")),
            ("foreigner", _("Foreigner")),
        ]

    @api.model
    def get_sale_fiscal_type_selection(self):
        sale_fiscal_type_list = self.env['l10n_latam.document.type'].sudo().search_read([],['name','l10n_do_ncf_type'])
        ncf_types = self.env['account.journal'].sudo()._get_l10n_do_ncf_types_data()
        print(sale_fiscal_type_list)
        # print(ncf_types.issued)
        return {
            "l10n_latam_document_type_id": self._fields['l10n_do_dgii_tax_payer_type'].selection,
            "sale_fiscal_type_list": sale_fiscal_type_list,
            # "sale_fiscal_type_vat": self.sale_fiscal_type_vat
        }

    def _get_l10n_do_expense_type(self):
        """Return the list of expenses needed in invoices to clasify accordingly to
        DGII requirements."""
        return [
            ("01", _("01 - Personal")),
            ("02", _("02 - Work, Supplies and Services")),
            ("03", _("03 - Leasing")),
            ("04", _("04 - Fixed Assets")),
            ("05", _("05 - Representation")),
            ("06", _("06 - Admitted Deductions")),
            ("07", _("07 - Financial Expenses")),
            ("08", _("08 - Extraordinary Expenses")),
            ("09", _("09 - Cost & Expenses part of Sales")),
            ("10", _("10 - Assets Acquisitions")),
            ("11", _("11 - Insurance Expenses")),
        ]

    l10n_do_dgii_tax_payer_type = fields.Selection(
        selection="_get_l10n_do_dgii_payer_types_selection",
        compute="_compute_l10n_do_dgii_payer_type",
        inverse="_inverse_l10n_do_dgii_tax_payer_type",
        string="Taxpayer Type",
        index=True,
        store=True,
    )
    l10n_do_expense_type = fields.Selection(
        selection="_get_l10n_do_expense_type",
        string="Cost & Expense Type",
        store=True,
    )
    is_fiscal_info_required = fields.Boolean(compute="_compute_is_fiscal_info_required")
    country_id = fields.Many2one(
        default=lambda self: self.env.ref("base.do")
        if self.env.user.company_id.country_id == self.env.ref("base.do")
        else False
    )

    @api.depends("l10n_do_dgii_tax_payer_type")
    def _compute_is_fiscal_info_required(self):
        for partner in self:
            if partner.l10n_do_dgii_tax_payer_type != "non_payer":
                partner.is_fiscal_info_required = True
            else:
                partner.is_fiscal_info_required = False
            if (
                partner.country_id == self.env.ref("base.do")
                and partner.l10n_do_dgii_tax_payer_type ==   "foreigner"
            ):
                raise UserError(
                    _(
                       "If is a Foreigner, Please Select the correct "
                       "Country"
                    )
                )


    @api.depends("vat", "country_id", "name")
    def _compute_l10n_do_dgii_payer_type(self):
        """ Compute the type of partner depending on soft decisions"""
        company_id = self.env["res.company"].search(
            [("id", "=", self.env.user.company_id.id)]
        )
        for partner in self:
            vat = str(partner.vat if partner.vat else partner.name)
            is_dominican_partner = bool(partner.country_id == self.env.ref("base.do"))

            if partner.country_id and not is_dominican_partner:
                partner.l10n_do_dgii_tax_payer_type = "foreigner"

            elif vat and (
                not partner.l10n_do_dgii_tax_payer_type
                or partner.l10n_do_dgii_tax_payer_type == "non_payer"
            ):
                if partner.country_id and is_dominican_partner:
                    if vat.isdigit() and len(vat) == 9:
                        if not partner.vat:
                            partner.vat = vat
                        if partner.name and "MINISTERIO" in partner.name:
                            partner.l10n_do_dgii_tax_payer_type = "governmental"
                        elif partner.name and any(
                            [n for n in ("IGLESIA", "ZONA FRANCA") if n in partner.name]
                        ):
                            partner.l10n_do_dgii_tax_payer_type = "special"
                        elif vat.startswith("1"):
                            partner.l10n_do_dgii_tax_payer_type = "taxpayer"
                        elif vat.startswith("4"):
                            partner.l10n_do_dgii_tax_payer_type = "nonprofit"
                        else:
                            partner.l10n_do_dgii_tax_payer_type = "taxpayer"

                    elif len(vat) == 11:
                        if vat.isdigit():
                            if not partner.vat:
                                partner.vat = vat
                            payer_type = (
                                "taxpayer"
                                if company_id.l10n_do_default_client == "taxpayer"
                                else "non_payer"
                            )
                            partner.l10n_do_dgii_tax_payer_type = payer_type
                        else:
                            partner.l10n_do_dgii_tax_payer_type = "non_payer"
                    else:
                        partner.l10n_do_dgii_tax_payer_type = "non_payer"
            elif not partner.l10n_do_dgii_tax_payer_type:
                partner.l10n_do_dgii_tax_payer_type = "taxpayer"
            else:
                partner.l10n_do_dgii_tax_payer_type = (
                    partner.l10n_do_dgii_tax_payer_type
                )

    def _convert_result(self, result):  # pragma: no cover
        """Translate SOAP result entries into dictionaries."""
        translation = {
            u'Cédula/RNC': 'rnc',
            u'Nombre Comercial':'commercial_name',
            u'Régimen de pagos': 'type',
            u'Categoría':"category",
            u'Nombre/Razón Social': 'name',
            'Estado': 'status',
            u'Actividad Economica': 'activity',
            u'Administracion Local': 'local_place',

        }
        return dict(
            (translation.get(key, key), value)
            for key, value in result.items())





    @api.onchange("vat")
    def _check_rnc(self):
        for partner_rnc in self:
            is_dominican_partner = bool(partner_rnc.country_id == self.env.ref("base.do"))
            if (
                partner_rnc.vat
                and is_dominican_partner
            ):
                if (
                    len(partner_rnc.vat) not in [9, 11]
                ):
                    raise UserError(
                        _(
                            "Check Vat Format or should not have any Caracter like '-'"
                        )
                    )

                if (
                    not (
                        (len(partner_rnc.vat) == 9 and rnc.is_valid(partner_rnc.vat))
                        or (len(partner_rnc.vat) == 11 and cedula.is_valid(partner_rnc.vat))
                    )
                ):

                    raise UserError(
                        _(
                            "Check Vat, Seems like it's not correct"
                        )
                    )
                # else:

                #     url = 'https://dgii.gov.do/app/WebApps/ConsultasWeb2/ConsultasWeb/consultas/rnc.aspx'
                #     session = requests.Session()
                #     session.headers.update({
                #         'User-Agent': 'Mozilla/5.0 (python-stdnum)',
                #     })

                #     document = lxml.html.fromstring(
                #     session.get(url, timeout=30).text)

                #     validation = document.find('.//input[@name="__EVENTVALIDATION"]').get('value')
                #     viewstate = document.find('.//input[@name="__VIEWSTATE"]').get('value')
                #     data = {
                #         '__EVENTVALIDATION': validation,
                #         '__VIEWSTATE': viewstate,
                #         'ctl00$cphMain$btnBuscarPorRNC': 'Buscar',
                #         'ctl00$cphMain$txtRNCCedula': partner_rnc.vat,
                #     }
                #     # Do the actual request
                #     document = lxml.html.fromstring(
                #         session.post(url, data=data, timeout=30).text)

                #     result = document.find('.//div[@id="cphMain_divBusqueda"]')
                #     message = document.findtext('.//*[@id="cphMain_lblInformacion"]')

                #     if result is not None:
                #         hearder = []
                #         keys = []

                #         for x in result.findall('.//tr/td'):
                #             if x.attrib:
                #                 hearder.append(x.text.strip())
                #             else:
                #                 keys.append(x.text.strip())

                #         if message:
                #             data = {
                #                 'validation_message': message.strip(),
                #             }
                #         else:
                #             data = {
                #                 'validation_message': 'Cédula/RNC es Válido',
                #             }

                #         data.update(zip(hearder, keys))


                #         info = self._convert_result(data)


                #         if "name" in info:
                #             info["name"] = " ".join(
                #                 re.split(r"\s+", info["name"], flags=re.UNICODE))

                #             partner_rnc.name = info["name"]

    def _inverse_l10n_do_dgii_tax_payer_type(self):
        for partner in self:
            partner.l10n_do_dgii_tax_payer_type = partner.l10n_do_dgii_tax_payer_type
