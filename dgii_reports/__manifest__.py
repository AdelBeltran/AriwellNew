# Part of Domincana Premium.
# See LICENSE file for full copyright and licensing details.
# © 2022-Adel Beltran <adelbeltran03@gamil.com>

{
    "name": "Declaraciones DGII",
    "summary": """
        Este módulo extiende las funcionalidades del l10n_do_accounting,
        integrando los reportes de declaraciones fiscales""",
    "author": "Adel Networks S,R,L",
    "license": "LGPL-3",
    "category": "Accounting",
    "version": "15.0.1.1.0",
    # any module necessary for this one to work correctly
    "depends": ["l10n_do_accounting", "l10n_latam_invoice"],

    'assets': {
        'web.assets_backend': [
            '/dgii_reports/static/src/js/widget.js',
            '/dgii_reports/static/src/less/dgii_reports.css'
        ],
    },
    "external_dependencies":{"python": ["pycountry"]},
    "data": [
        # "data/invoice_service_type_detail_data.xml",
        # "data/account_fiscal_type_data.xml",
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "views/res_partner_views.xml",
        "views/account_account_views.xml",
        "views/account_invoice_views.xml",
        "views/dgii_report_views.xml",
        # "views/dgii_report_templates.xml",
        "wizard/dgii_report_regenerate_wizard_views.xml",
    ],
}
