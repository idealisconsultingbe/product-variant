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


class EkiSalesProductTemplate(models.Model):
    _inherit = "product.template"

    @api.multi
    @api.depends('eki_price_ratio', 'standard_price')
    def _compute_list_price(self):
        for product in self:
            ratio = 1
            if product.eki_price_ratio:
                ratio = product.eki_price_ratio
            product.list_price = ratio * product.standard_price

    eki_price_ratio = fields.Float("Ratio for Price", digits=dp.get_precision('Discount'), default=0.0, help="Public price is calculating from cost * Ratio")
    list_price = fields.Float(readonly=True, compute=_compute_list_price)
