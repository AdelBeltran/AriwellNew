## Part of Domincana Premium.
# See LICENSE file for full copyright and licensing details.
# © 2022-Adel Beltran <adelbeltran03@gamil.com>

# This file is part of NCF Manager.

# NCF Manager is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# NCF Manager is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with NCF Manager.  If not, see <https://www.gnu.org/licenses/>.

{
    'name': "NCF POS",
    'summary': """
        Incorpora funcionalidades de facturación con NCF al POS
        """,
    'author': "Adel Networks S,R,L",
    'license': 'LGPL-3',
    'category': 'Localization',
    'version': '12.0.1.1.0',

    # any module necessary for this one to work correctly
    'depends': ['l10n_do_accounting', 'point_of_sale'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        # 'views/templates.xml',
        'views/pos_config.xml',
        'views/pos_view.xml',
        'views/pos_payment_method_view.xml',
        'data/data.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'l10n_do_pos/static/src/libs/jquery-autocomplete-ui.css',
            'l10n_do_pos/static/src/css/l10n_do_pos.css',
            'l10n_do_pos/static/src/js/utils.js',
            'l10n_do_pos/static/src/js/models.js',
            'l10n_do_pos/static/src/js/screens.js',
            'l10n_do_pos/static/src/js/db.js',
        ],
        'web.assets_qweb': [
            'l10n_do_pos/static/src/xml/**/*',
        ],
    },
}
            # 'l10n_do_pos/static/src/xml/pos.xml',
            # 'l10n_do_pos/static/src/xml/ncf_ticket.xml',
