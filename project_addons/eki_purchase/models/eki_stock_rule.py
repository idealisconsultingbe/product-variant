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


class EkiStockRule(models.Model):
    _inherit = 'stock.rule'

    @api.multi
    def _run_buy(self, product_id, product_qty, product_uom, location_id, name, origin, values):
        # New function add all product from the supplier into the PO
        def _add_product_from_supplier_id(po):
            if po.partner_id:
                now = fields.Datetime.now()
                supplier_infos = po.env['product.supplierinfo'].search(
                    [('name', '=', po.partner_id.id), '|', '&', ('date_start', '<=', now), ('date_end', '>=', now), '&',
                     ('date_start', '=', False), ('date_end', '=', False)])
                for supplier_info in supplier_infos:
                    product = supplier_info.product_id if supplier_info.product_id else supplier_info.product_tmpl_id.product_variant_id
                    if product and product not in po.order_line.mapped('product_id'):
                        vals = {'name': product.name,
                                'product_id': product.id,
                                'product_qty': 0,
                                'product_uom': supplier_info.product_uom.id,
                                'price_unit': product.list_price,
                                'date_planned': now,
                                'order_id': po.id}
                        po.env['purchase.order.line'].sudo().create(vals)
        cache = {}
        suppliers = product_id.seller_ids \
            .filtered(lambda r: (not r.company_id or r.company_id == values['company_id']) and (
                    not r.product_id or r.product_id == product_id))
        if not suppliers:
            msg = _('There is no vendor associated to the product %s. Please define a vendor for this product.') % (
            product_id.display_name,)
            raise UserError(msg)
        supplier = self._make_po_select_supplier(values, suppliers)
        partner = supplier.name
        # we put `supplier_info` in values for extensibility purposes
        values['supplier'] = supplier

        domain = self._make_po_get_domain(values, partner)
        if domain in cache:
            po = cache[domain]
        else:
            po = self.env['purchase.order'].sudo().search([dom for dom in domain])
            po = po[0] if po else False
            cache[domain] = po
        if not po:
            vals = self._prepare_purchase_order(product_id, product_qty, product_uom, origin, values, partner)
            company_id = values.get('company_id') and values['company_id'].id or self.env.user.company_id.id
            po = self.env['purchase.order'].with_context(force_company=company_id).sudo().create(vals)
            _add_product_from_supplier_id(po) #ADD all products from the supplier
            cache[domain] = po
        elif not po.origin or origin not in po.origin.split(', '):
            if po.origin:
                if origin:
                    po.write({'origin': po.origin + ', ' + origin})
                else:
                    po.write({'origin': po.origin})
            else:
                po.write({'origin': origin})

        # Create Line
        po_line = False
        for line in po.order_line:
            if line.product_id == product_id and line.product_uom == product_id.uom_po_id:
                if line._merge_in_existing_line(product_id, product_qty, product_uom, location_id, name, origin,
                                                values):
                    vals = self._update_purchase_order_line(product_id, product_qty, product_uom, values, line, partner)
                    po_line = line.write(vals)
                    break
        if not po_line:
            vals = self._prepare_purchase_order_line(product_id, product_qty, product_uom, values, po, partner)
            self.env['purchase.order.line'].sudo().create(vals)

    # WARNING! BReaking the standard HUGE impact.
    # The behavior when creating a PO line created from the scheduler or from an SO could change.
    def _update_purchase_order_line(self, product_id, product_qty, product_uom, values, line, partner):
        res = super(EkiStockRule, self)._update_purchase_order_line(product_id, product_qty, product_uom, values, line, partner)
        stock_warehouse_orderpoint = self.env['stock.warehouse.orderpoint'].search([('product_id', '=', product_id.id), ('product_min_qty', '>', product_id.virtual_available)], order="product_min_qty", limit=1)
        if stock_warehouse_orderpoint and res['product_qty'] + product_id.virtual_available > stock_warehouse_orderpoint.product_max_qty:
            res.update({'product_qty': stock_warehouse_orderpoint.product_max_qty-product_id.virtual_available}) # Overwrite the existing qty
        return res
