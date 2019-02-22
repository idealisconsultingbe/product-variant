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
from odoo.exceptions import UserError, ValidationError

class EkiAccountInvoice(models.Model):
    _inherit = "account.invoice"

    def adapt_supplierinfo(self):
        product_supplierinfo_obj = self.env['product.supplierinfo']
        # For each invoice, we look for product_supplierinfo with same partner/product key
        for invoice in self:
            for invoice_line in invoice.invoice_line_ids:
                supplierinfos = product_supplierinfo_obj.search([('name', '=', invoice.partner_id.id),
                                                                ('product_id', '=', invoice_line.product_id.id),
                                                                 ('min_qty', '<=', invoice_line.quantity),
                                                                 ])
                if supplierinfos:
                    # If we found only one supplierinfo, we apply the logic on it
                    if len(supplierinfos) == 1:
                        # If the price is different, then we put the flag on and adapt the last price field
                        if supplierinfos.price != invoice_line.price_unit:
                            supplierinfos.write({
                                'eki_last_supplier_price': invoice_line.price_unit,
                                'eki_price_has_changed': True})
                    # If we fond more than 1 supplierinfo, we need to get the last one
                    elif len(supplierinfos) > 1:
                        lastsupplierinfo = None
                        delta_min_qty = 0
                        for supplierinfo in supplierinfos:
                            # In the logic, we always state that if date_to is not filled, then it's the last one
                            if not lastsupplierinfo:
                                lastsupplierinfo = supplierinfo
                                delta_min_qty = invoice_line.quantity - supplierinfo.min_qty

                            else:
                                if not supplierinfo.date_end and (invoice_line.quantity - supplierinfo.min_qty) < delta_min_qty:
                                    lastsupplierinfo = supplierinfo
                                    delta_min_qty = invoice_line.quantity - supplierinfo.min_qty
                                # If we need to compare two suppliers info based on date,
                                # the one with the bigger date_to is chose if min_qty is ok
                                elif supplierinfo.date_end:
                                    if lastsupplierinfo.date_end:
                                        if supplierinfo.date_end > lastsupplierinfo.date_end \
                                            and supplierinfo.min_qty > lastsupplierinfo.min_qty\
                                            and (invoice_line.quantity - supplierinfo.min_qty) < delta_min_qty:
                                            lastsupplierinfo = supplierinfo
                                            delta_min_qty = invoice_line.quantity - supplierinfo.min_qty
                                        elif supplierinfo.min_qty > lastsupplierinfo.min_qty\
                                            and (invoice_line.quantity - supplierinfo.min_qty) < delta_min_qty:
                                            lastsupplierinfo = supplierinfo
                                            delta_min_qty = invoice_line.quantity - supplierinfo.min_qty

                        if lastsupplierinfo.price != invoice_line.price_unit:
                            lastsupplierinfo.write({
                                'eki_last_supplier_price': invoice_line.price_unit,
                                'eki_price_has_changed': True})

    def action_invoice_open(self):
        for invoice in self.filtered(lambda x: x.type == 'in_invoice'):
            # For each invoice, we search another invoice (supplier) with the same reference.
            # If we found one based on the criteria, then we raise an error to the user
            if invoice.search([('id', '!=', invoice.id), ('reference', '=', invoice.reference),
                               ('state', 'not in', ('draft', 'cancel')),
                               ('partner_id', '=', invoice.partner_id.id)]):
                raise UserError(_('This reference is already used by another Vendor Bill'))

        res = super(EkiAccountInvoice, self).action_invoice_open()

        self.adapt_supplierinfo()

        return res