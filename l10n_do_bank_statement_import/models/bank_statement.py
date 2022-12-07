# -*- coding: utf-8 -*-
import logging
import chardet
import codecs
import calendar
import unicodedata
from datetime import datetime
from odoo.tools import pycompat
from odoo.exceptions import Warning
from odoo import models, fields, api, _
_logger = logging.getLogger(__name__)

from io import StringIO
import io

try:
    import csv
except ImportError:
    _logger.debug('Cannot `import csv`.')
    _logger.debug('Cannot `import cStringIO`.')
try:
    import base64
except ImportError:
    _logger.debug('Cannot `import base64`.')
    
BOM_MAP = {
    'utf-16le': codecs.BOM_UTF16_LE,
    'utf-16be': codecs.BOM_UTF16_BE,
    'utf-32le': codecs.BOM_UTF32_LE,
    'utf-32be': codecs.BOM_UTF32_BE,
}

class account_bank_statement_wizard(models.TransientModel):
    _name= "account.bank.statement.wizard"

    file = fields.Binary(string="Archivo")
    file_opt = fields.Selection(
        [('excel','Excel'),('csv','CSV')],
        string="Tipo De Archivo", default='csv')

    def import_file(self):
        #Search the actual Bank Statement
        active_id = self._context.get('active_ids')
        bs_id = self.env["account.bank.statement"].browse(active_id)
        
        bank_st = bs_id.journal_id.statement_import_type
        format_import = 'csv'
        file_path = self.file

        if not bank_st or bank_st =='manual':
            raise Warning(_('''Formato de Extracto Invalido\n
             vaya a  Diarios > Cuenta Bancaria > Formato de Conciliacion \n
             Para poder Importar su Extracto.'''))
        
        if not file_path or file_path == "":
            raise Warning(_('Importar es imposible sin el archivo'))
        
        if format_import == 'csv':
            fields, data_lines = self._read_csv_data(file_path)
        
        if not data_lines:
            raise Warning(_("El Archivo No Tiene Informacion."))
        
        _logger.info("Iniciacion de Importacion de Datos De Extracto Bancarios")

        if format_import == 'csv' and bank_st =='bpd':
            self._import_csv_bpd(fields, data_lines, bs_id)
        
        if format_import == 'csv' and bank_st =='res':
            self._import_csv_res(fields, data_lines, bs_id)

        if format_import == 'csv' and bank_st =='bhd':
            self._import_csv_bhd(fields, data_lines, bs_id)

    def _read_csv_data(self, csv_data):

        csv_data = base64.b64decode(csv_data)
        encoding = chardet.detect(csv_data)['encoding'].lower()
        bom = BOM_MAP.get(encoding)
        
        if bom and csv_data.startswith(bom):
            encoding = encoding[:-2]

        if encoding != 'utf-8':
            csv_data = csv_data.decode(encoding).encode('utf-8')

        separator = ','
        for candidate in (',', ';', '\t', ' ', '|', unicodedata.lookup('unit separator')):
            it = pycompat.csv_reader(
                io.BytesIO(csv_data),
                quoting=csv.QUOTE_ALL, 
                skipinitialspace=True, quotechar='"', delimiter=candidate)
            w = None
            for row in it:
                width = len(row)
                if w is None:
                    w = width
                if width == 1 or width != w:
                    break 
            else:
                separator = candidate
                break

        data_lines = []
        data = pycompat.csv_reader(
            io.BytesIO(csv_data), quotechar='"',
            quoting=csv.QUOTE_ALL, skipinitialspace=True,
            delimiter=separator)
        
        fields = next(data)
        for row in data:
            items = dict(zip(fields, row))
            data_lines.append(items)
        return fields, data_lines
    

    def _import_csv_bpd(self, fields, data_lines, bs_id):
        statement_line = []

        debit_keywords = ['pago impuesto',]
        credit_keyword = ['crédito', 'credito', 'cr pago','cr�dito']
        
        for data in data_lines:
            flag = 0
            txn_type = data.get('Descripción Corta') or data.get('Descripci�n Corta')
            payment_ref = data.get('Descripción') or data.get('Descripci�n')
            amount = data.get("Monto Transacci�n") or data.get('Monto Transacción')
            serial_no = data.get("No. Serial")
            partner_name = ""
            if len(serial_no) == 9:
                partner_name = self._find_partner(int(serial_no))

            for keyword in credit_keyword:
                if txn_type:
                    if keyword in txn_type.lower():
                        flag = 1
                        break
            
            if not txn_type:
                for keyword in debit_keywords:
                    if keyword in payment_ref.lower():
                        flag = 0
                        break

            if not payment_ref:
                raise Exception()
            
            date = datetime.strptime(data.get('Fecha Posteo'), '%d/%m/%Y').date()
            statement_line.append((0, 0, {'date': date,
                'payment_ref': " ".join(payment_ref.split()),
                'partner_id': partner_name if partner_name else "",
                'ref': serial_no,
                'amount': float(amount) if flag else -abs(float(amount))}))
        
        self._create_statement_lines(statement_line, bs_id)


    def _import_csv_bhd(self, fields, data_lines, bs_id):
        statement_line = []
        tax_comm = ['impuesto','288-04']
        sum_ncf = []
        unique_ncf = []
        head = ['ncf', 'date', 'name' , 'amount' ]
        for data in data_lines:
            amount = 0
            txn_type = data.get('NCF')
            payment_ref = data.get('Desc. Movimiento')
            debit = data.get("Débito") or data.get("D�bito") or data.get("Debito")
            credit = data.get("Crédito") or data.get("Cr�dito") or data.get("Credito")
            date = data.get('Fecha').replace(' ','')
            date = datetime.strptime(date, '%d/%m/%Y').date()

            amount = float(credit) - float(debit)

            for keyword in tax_comm:
                if txn_type:
                    if keyword in payment_ref.lower():
                        payment_ref = "Impuesto Ley 288-04"
                    else:
                        payment_ref = "Comision Bancaria"
            
            if txn_type:
                ncf = [txn_type, date, payment_ref, amount]
                items = dict(zip(head, ncf))
                sum_ncf.append(items)
                if txn_type not in unique_ncf:
                    unique_ncf.append(txn_type)
                continue
               
            statement_line.append((0, 0, {'date': date,
                'payment_ref': " ".join(payment_ref.split()),
                'amount': amount }))
        
        if sum_ncf:
            info = []
            for n in unique_ncf:
                amount = 0
                name = ''
                date = ''
                for item in sum_ncf:
                    if n == item.get('ncf'):
                        amount =+ amount + item.get('amount')
                        name = item.get('name')
                        day = calendar.monthrange(item.get('date').year,item.get('date').month)[1]
                        date_f = "{}/{}/{}".format(day,item.get('date').month, item.get('date').year)
                        date = datetime.strptime(date_f, '%d/%m/%Y').date()
                info.append((0, 0, {'date': date, 'payment_ref': n, 'ref': name, 'amount': round(amount, 2, )}))

        lines = statement_line + info

        self._create_statement_lines(lines, bs_id)

    def _import_csv_res(self, fields, data_lines, bs_id):
        
        statement_line = []

        for data in data_lines:
            amount = 0

            payment_ref = data.get('Descripción') or data.get('Descripci�n')
            serial_no = data.get("Id de transacción") or data.get("Id de transacci�n")
            debit = data.get("Débito") or data.get("D�bito") or data.get("Debito")
            credit = data.get("Crédito") or data.get("Cr�dito") or data.get("Credito")
            
            if serial_no:
                partner_name = self._find_partner(int(serial_no))

            if payment_ref == None:
                payment_ref = data.get("Concepto")
            
            amount = float(credit.replace(',','')) - float(debit.replace(',',''))
            
            date = datetime.strptime(data.get('Fecha'), '%d/%m/%Y').date()
            statement_line.append((0, 0, {'date': date,
                'payment_ref': " ".join(payment_ref.split()),
                'partner_id': partner_name,
                'ref' : serial_no,
                'amount': amount}))
        
        self._create_statement_lines(statement_line, bs_id)

    def _find_partner(self,account):
        partner_bank = self.env['res.partner.bank'].search([('acc_number','=', str(account))])

        if partner_bank:
            return partner_bank.partner_id.id
        else:
            return

    def _create_statement_lines(self, statement_line, bs_id):
        if statement_line:
            bs_id.line_ids.unlink()
            bs_id.write({'line_ids': statement_line})



 