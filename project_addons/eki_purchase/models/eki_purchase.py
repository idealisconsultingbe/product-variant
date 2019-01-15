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


class EkiProductTemplate(models.Model):
    _inherit = "purchase.order"

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            now = fields.Datetime.now()
            supplier_infos = self.env['product.supplierinfo'].search([('name', '=', self.partner_id.id), '|', '&', ('date_start', '<', now), ('date_end', '>', now), '&', ('date_start', '=', False), ('date_end', '=', False)])
            for supplier_info in supplier_infos:
                self.update({
                    'order_line': [(0, 0, {
                        'name': supplier_info.product_id.name,
                        'product_id': supplier_info.product_id.id,
                        'product_uom_qty': 0,
                        'product_uom': supplier_info.product_id.uom_id.id,
                        'price_unit': supplier_info.product_id.list_price,
                    })]
                })

