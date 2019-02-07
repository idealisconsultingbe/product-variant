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
    'name': 'Ekivrac Base',
    'category': 'Ekivrac',
    'version': '1.0',
    'website': 'https://www.idealisconsulting.com/',
    'description': """
Ekivrac Module

Main module
        """,
    'depends': [
        'stock',
        'product',
        'sale',
        'sale_management',
        'sale_purchase',
        'point_of_sale',
    ],
    'data': [
        'views/eki_partner_view.xml',
        'views/eki_product_view.xml',
        'views/eki_sale_view.xml',

        'security/ir.model.access.csv',
    ],
    'qweb': [
    ],
    'demo': [
    ],
    'installable': True,
    'application': True,
}
