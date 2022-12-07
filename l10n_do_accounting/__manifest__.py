# Part of Domincana Premium.
# See LICENSE file for full copyright and licensing details.
# © 2022-Adel Beltran <adelbeltran03@gamil.com>

{
    "name": "Fiscal Accounting (Rep. Dominicana)",
    "summary": """
        Este módulo implementa la administración y gestión de los números de
         comprobantes fiscales para el cumplimento de la norma 06-18 de la
         Dirección de Impuestos Internos en la República Dominicana.""",
    "author": "Adel Networks S,R,L",
    "category": "Localization",
    "license": "LGPL-3",
    "version": "15.0.1.0.1",
    # any module necessary for this one to work correctly
    "depends": ["web","l10n_latam_invoice", "l10n_do"],
    # always loaded
    "data": [
        #'data/ir_config_parameters.xml', removed in favor of another module
        "security/res_groups.xml",
        "security/ir.model.access.csv",
        "data/l10n_latam.document.type.csv",
        "wizard/account_move_reversal_views.xml",
        "views/account_move_tax_views.xml",
        "views/account_tax_views.xml",
        "wizard/account_move_cancel_views.xml",
        "wizard/account_fiscal_sequence_validate_wizard_views.xml",
        "views/account_fiscal_sequence_views.xml",
        "views/res_config_settings_view.xml",
        "views/account_move_views.xml",
        "views/res_partner_views.xml",
        "views/res_company_views.xml",
        "views/account_journal_views.xml",
        "views/account_report.xml",
        "views/l10n_latam_document_type_views.xml",
        "views/report_templates.xml",
        "views/report_invoice.xml",
        "views/account_journal_views.xml",
        # "views/backend_js.xml",
        

    ],
    # "external_dependencies": {"python": ["python-stdnum==1.13"]}, removed in favor of another module
    'assets': {
        'web.assets_backend': [
            # 'l10n_do_accounting/static/src/js/l10n_do_accounting.js',
            'l10n_do_accounting/static/src/js/fiscal_sequence_warning.js',
            'l10n_do_accounting/static/src/scss/fiscal_sequence_warning.scss'
            
            
        ], 
    },
    # only loaded in demonstration mode
    "demo": [
        "demo/res_partner_demo.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
}
