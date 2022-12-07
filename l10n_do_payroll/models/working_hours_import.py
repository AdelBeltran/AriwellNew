# -*- coding: utf-8 -*-

from odoo import api, fields, models


class WorkingHoursImport(models.Model):
    _name = 'working.hours.import'
    _description = 'Importacion de horas trabajadas de los emprleados'

    name = fields.Char(compute='_compute_name')
    employee_id = fields.Many2one('hr.employee', string="Empleado", required=True)
    date_from = fields.Date(string="Fecha desde", required=True)
    date_to = fields.Date(string="Fecha hasta", required=True)
    hours_amount = fields.Float(string="Horas normales", required=True)
    extra_hours_amount = fields.Float(string="Horas extras", required=True)
    holiday_hours_amount = fields.Float(string="Horas feriadas", required=True)

    @api.depends('employee_id', 'date_from', 'date_to')
    def _compute_name(self):
        for rec in self:
            rec.name = "Horas: {0}/{1} - {2}".format(rec.employee_id.name, rec.date_from, rec.date_to)


