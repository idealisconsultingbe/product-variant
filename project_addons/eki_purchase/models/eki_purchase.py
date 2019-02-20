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
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import datetime


class EkiPurchaseOrder(models.Model):
    _inherit = "purchase.order"

    # Output:   The tax of the product.
    def _get_tax(self, product):
        self.ensure_one()
        taxes = product.supplier_taxes_id
        fpos = self.fiscal_position_id
        taxes_id = fpos.map_tax(taxes, product, self.partner_id.name) if fpos else taxes
        if taxes_id:
            taxes_id = taxes_id.filtered(lambda x: x.company_id.id == self.company_id.id)
        return taxes_id

    # Output:   The price_unit of the product depending on the taxe and the supplier_info.
    def _get_price_unit(self, product, taxe, supplier_info):
        self.ensure_one()
        price_unit = self.env['account.tax']._fix_tax_included_price_company(supplier_info.price, product.supplier_taxes_id, taxe, self.company_id.id) if supplier_info else 0.0
        if price_unit and supplier_info and self.currency_id and supplier_info.currency_id != self.currency_id:
            price_unit = supplier_info.currency_id._convert(
                price_unit, self.currency_id, self.company_id, self.date_order or fields.Date.today())
        return price_unit

    def _prepare_order_line(self, product, product_qty, product_uom, supplier_info=False):
        procurement_uom_po_qty = product_uom._compute_quantity(product_qty, product.uom_po_id)
        supplier_info = supplier_info if supplier_info else product._select_seller(partner_id=self.partner_id,
                                                                                   quantity=procurement_uom_po_qty,
                                                                                   date=self.date_order and self.date_order.date(),
                                                                                   uom_id=product.uom_po_id)
        taxes_id = self._get_tax(product)
        price_unit = self._get_price_unit(product, taxes_id, supplier_info)
        date_planned = self.env['purchase.order.line']._get_date_planned(supplier_info, po=self).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        return {
            'name': product.name,
            'product_id': product.id,
            'product_qty': product_qty,
            'price_unit': price_unit,
            'product_uom': product_uom.id,
            'taxes_id': [(6, 0, taxes_id.ids)],
            'date_planned': date_planned,
        }

    # Input:    product_not_to_add is a list of id
    # Output:   A list of tuples (to be used for creating purchase.order.line). Tuples have the following structure: (0, 0, dict), the dict contain the details of a purchase.order.line.
    #           Add one tuple into the list for every product sold by the partner of the PO, except for product that have their id into the list product_not_to_add.
    def _add_product_from_supplier(self, product_not_to_add=False):
        self.ensure_one()
        values = []
        if self.partner_id:
            now = fields.Datetime.now()
            product_in_values = product_not_to_add if product_not_to_add else []
            supplier_infos = self.env['product.supplierinfo'].search([('name', '=', self.partner_id.id), '|', '&', ('date_start', '<=', now), ('date_end', '>=', now), '&', ('date_start', '=', False), ('date_end', '=', False)])
            for supplier_info in supplier_infos:
                product = supplier_info.product_id if supplier_info.product_id else supplier_info.product_tmpl_id.product_variant_id
                if product and not product.eki_is_return and product.id not in product_in_values:
                    product_in_values.append(product.id)
                    values.append((0, 0, self._prepare_order_line(product, 0, supplier_info.product_uom, supplier_info)))
        return values

    # Input:    product_details is a list of dicts, dicts have the following structure {'product_id': product.product, 'product_gty', int}
    #           values is a list of tuples, these contains the values that are going to be add to the PO order_line.
    # Output:   For every product.product contained int the product_details we do the following steps:
    #           1. Check if the product.product is linked to an eki_return product
    #           2. If it is we add one tuple into values with the details of the eki_return product and we adapt the quantity (product.product.qty == eki_return.qty)
    #           3. Tuples with details for the same eki_return are merged together.
    def _add_eki_return(self, product_details, values):
        self.ensure_one()
        # We look forward return to add in the PO based on eki_return field
        product_to_add = []
        lines_with_return = list(filter(lambda x: x['product_id'].eki_return, product_details))
        # If we found some, we add it in the dict
        for line in lines_with_return:
            # We add one line per return product, thus we had to sum on all product with the same eki_return
            if line['product_id'].eki_return.id not in product_to_add:
                line_with_same_return = list(
                    filter(lambda x: x['product_id'].eki_return == line['product_id'].eki_return, lines_with_return))
                qty = sum(x['product_qty'] for x in line_with_same_return)
                values.append((0, 0, self._prepare_order_line(line['product_id'].eki_return, qty, line['product_id'].eki_return.uom_po_id)))
                product_to_add.append(line['product_id'].eki_return.id)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        values = self._add_product_from_supplier()
        product_in_po = [{'product_id': self.env['product.product'].browse(line[2]['product_id']),
                          'product_qty': line[2]['product_qty']} for line in values]
        self._add_eki_return(product_in_po, values)
        self.update({'order_line': values})

    @api.multi
    def button_confirm(self):
        for order in self:
            if order.partner_id.eki_franco > 0.0 and order.amount_total < order.partner_id.eki_franco:
                raise UserError(_("The total amount is less than the minimum amount ({} < {}) for the partner {}").format(
                    order.amount_total, order.partner_id.eki_franco, order.partner_id.name))
        return super(EkiPurchaseOrder, self).button_confirm()

    @api.multi
    def update_vidange(self):
        for purchase in self:
            values = []
            for line in purchase.order_line.filtered(lambda x:x.product_id.eki_is_return):
                purchase.update({'order_line': [(2, line.id)]})
            product_in_po = [{'product_id': line.product_id, 'product_qty': line.product_qty} for line in purchase.order_line]
            self._add_eki_return(product_in_po, values)
            if values:
                purchase.update({'order_line': values})


class EkiPurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    eki_is_product_under_min_stock = fields.Boolean(string='Product under min stock', compute='_compute_product_under_min_stock')
    eki_product_qty_available = fields.Float(string='Available quantity', related='product_id.qty_available', readonly=True)
    eki_product_sales_x_days = fields.Integer(string='Sales last days', compute='_compute_eki_product_sales_x_days', readonly=True)
    eki_discount = fields.Float(string='Discount (%)', digits=dp.get_precision('Discount'), compute='_compute_amount')
    eki_previous_qty = fields.Float(string='Previous product qty')

    @api.depends('product_id.seller_ids', 'product_qty', 'price_unit', 'taxes_id')
    def _compute_amount(self):
        for line in self:
            if not line.product_id.eki_is_return:
                now = fields.Datetime.now()
                supplier = line.order_id.partner_id
                supplier_info = line.product_id.seller_ids.filtered(lambda x:x.name.id == supplier.id and x.min_qty <= line.product_qty and ((x.date_start == False or x.date_start <= now) and (x.date_end == False or x.date_end >= now)))
                supplier_info = supplier_info.sorted(lambda x: x.min_qty, reverse=True)
                line.eki_discount = supplier_info[0].eki_discount if supplier_info else 0.0
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





