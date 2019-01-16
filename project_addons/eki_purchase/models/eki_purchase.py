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


class EkiPurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            now = fields.Datetime.now()
            values = []
            supplier_infos = self.env['product.supplierinfo'].search([('name', '=', self.partner_id.id), '|', '&', ('date_start', '<=', now), ('date_end', '>=', now), '&', ('date_start', '=', False), ('date_end', '=', False)])
            for supplier_info in supplier_infos:
                product = supplier_info.product_id if supplier_info.product_id else supplier_info.product_tmpl_id.product_variant_id
                if product:
                    values.append((0,0,{
                            'name': product.name,
                            'product_id': product.id,
                            'product_qty': 0,
                            'product_uom': supplier_info.product_uom.id,
                            'price_unit': product.list_price,
                            'date_planned': now,
                        }))
            self.update({'order_line': values})


class EkiPurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    eki_is_product_under_min_stock = fields.Boolean(string='Product under min stock', compute='_compute_product_under_min_stock')

    @api.one
    def _compute_product_under_min_stock(self):
        order_points = self.env['stock.warehouse.orderpoint'].search([('product_id', '=', self.product_id.id)])
        for order_point in order_points:
            if order_point.product_min_qty > self.product_id.qty_available:
                self.eki_is_product_under_min_stock = True
                return

        self.eki_is_product_under_min_stock = False
