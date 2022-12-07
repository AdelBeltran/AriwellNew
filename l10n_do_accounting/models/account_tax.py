from odoo import models, fields


class AccountTax(models.Model):
    _inherit = "account.tax"

    purchase_tax_type = fields.Selection(
        [
            ("itbis", "ITBIS Pagado"),
            ("ritbis", "ITBIS Retenido"),
            ("isr", "ISR Retenido"),
            ("rext", "Pagos al Exterior (Ley 253-12)"),
            ("none", "No Deducible"),
        ],
        default="none",
        string="Tipo de Impuesto en Compra",
    )
    isr_retention_type = fields.Selection(
        [
            ("01", "Alquileres"),
            ("02", "Honorarios por Servicios"),
            ("03", "Otras Rentas"),
            ("04", "Rentas Presuntas"),
            ("05", u"Intereses Pagados a Personas Jurídicas"),
            ("06", u"Intereses Pagados a Personas Físicas"),
            ("07", u"Retención por Proveedores del Estado"),
            ("08", u"Juegos Telefónicos"),
        ],
        string="Tipo de Retención en ISR",
    )
