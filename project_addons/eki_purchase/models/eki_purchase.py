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

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons import decimal_precision as dp
import datetime


class EkiPurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            now = fields.Datetime.now()
            values = []
            product_in_values = []
            supplier_infos = self.env['product.supplierinfo'].search([('name', '=', self.partner_id.id), '|', '&', ('date_start', '<=', now), ('date_end', '>=', now), '&', ('date_start', '=', False), ('date_end', '=', False)])
            for supplier_info in supplier_infos:
                product = supplier_info.product_id if supplier_info.product_id else supplier_info.product_tmpl_id.product_variant_id
                if product and product.id not in product_in_values:
                    product_in_values.append(product.id)
                    values.append({
                            'name': product.name,
                            'product_id': product.id,
                            'product_qty': 0,
                            'product_uom': supplier_info.product_uom.id,
                            'price_unit': product.price,
                            'date_planned': now,
                        })
            self.update({'order_line': values})


class EkiPurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    eki_is_product_under_min_stock = fields.Boolean(string='Product under min stock', compute='_compute_product_under_min_stock')
    eki_product_qty_available = fields.Float(string='Available quantity', related='product_id.qty_available', readonly=True)
    eki_product_sales_x_days = fields.Integer(string='Sales last days', compute='_compute_eki_product_sales_x_days', readonly=True)
    eki_discount = fields.Float(string='Discount (%)', digits=dp.get_precision('Discount'), compute='_compute_amount')

    @api.depends('product_id.seller_ids', 'product_qty', 'price_unit', 'taxes_id')
    def _compute_amount(self):
        for line in self:
            if not line.product_id.eki_is_return:
                now = fields.Datetime.now()
                supplier = line.order_id.partner_id
                supplier_info = line.product_id.seller_ids.filtered(lambda x:x.name.id == supplier.id and x.min_qty <= line.product_qty and ((x.date_start == False or x.date_start <= now) and (x.date_end == False or x.date_end >= now)))
                supplier_info = supplier_info.search([], order="min_qty desc", limit=1)
                line.eki_discount = supplier_info.eki_discount if supplier_info else 0.0
            vals = line._prepare_compute_all_values()
            vals['price_unit'] = vals['price_unit'] * (1 - (line.eki_discount or 0.0) / 100.0)
            taxes = line.taxes_id.compute_all(
                vals['price_unit'],
                vals['currency_id'],
                vals['product_qty'],
                vals['product'],
                vals['partner'])
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

    @api.one
    def _compute_product_under_min_stock(self):
        order_points = self.env['stock.warehouse.orderpoint'].search([('product_id', '=', self.product_id.id)])
        for order_point in order_points:
            if order_point.product_min_qty > self.product_id.qty_available:
                self.eki_is_product_under_min_stock = True
                return

        self.eki_is_product_under_min_stock = False

    @api.one
    def _compute_eki_product_sales_x_days(self):
        now = fields.Datetime.now()
        start_date = now - datetime.timedelta(days=self.env.user.company_id.eki_show_days_sales_po)
        pos_order_lines = self.env['pos.order.line'].search([('product_id', '=', self.product_id.id), ('eki_date_order', '<', now), ('eki_date_order', '>', start_date)])
        self.eki_product_sales_x_days = 0
        for pos_order_line in pos_order_lines:
            self.eki_product_sales_x_days += pos_order_line.qty
