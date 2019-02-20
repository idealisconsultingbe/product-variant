# -*- coding: utf-8 -*-
##############################################################################
#
# This module is developed by Idealis Consulting SPRL
# Copyright (C) 2019 Idealis Consulting SPRL (<http://idealisconsulting.com>).
# All Rights Reserved
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Ekivrac Barcode',
    'category': 'Ekivrac',
    'version': '1.0',
    'website': 'https://www.idealisconsulting.com/',
    'description': """
Ekivrac Module

Barcode Module Customization
        """,
    'depends': [
        'stock_barcode',
        'eki_product',
    ],
    'data': [
        'views/eki_barcode_assets.xml',
        'views/eki_product_lot_view.xml',
        'data/eki_data.xml',
    ],
    'qweb': [
        'static/src/xml/eki_barcode_templates.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'application': True,
}
