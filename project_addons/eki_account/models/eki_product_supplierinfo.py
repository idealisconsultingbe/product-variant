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

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp


class EkiSupplierInfo(models.Model):
    _inherit = "product.supplierinfo"

    @api.multi
    def _validate_new_price(self):
        for supplierinfo in self.filtered(lambda x: x.eki_price_has_changed):
            supplierinfo.write({
                'price': supplierinfo.eki_last_supplier_price,
                'eki_last_supplier_price': 0.0,
                'eki_price_has_changed': False})

    @api.multi
    def _refuse_new_price(self):
        for supplierinfo in self.filtered(lambda x: x.eki_price_has_changed):
            supplierinfo.write({
                'eki_last_supplier_price': 0.0,
                'eki_price_has_changed': False})

    eki_last_supplier_price = fields.Float(string='Last Supplier Price')
    eki_price_has_changed = fields.Boolean(string='Price Change', default=False)


