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

from odoo import api, models, fields, _


class EkiSearchModifiedProductPrice(models.TransientModel):
    _name = "search.modified.product.price"

    def find_product_price_changed(self):
        product_ids = self.env['product.product'].search([('date_last_changed_price', '>=', self.date)])
        self.write({'product_ids': [(6, 0, product_ids.ids)]})
        try:
            view_form_id = self.env.ref('eki_pos.eki_found_product_price_form_view').id
        except ValueError:
            view_form_id = False
        return {
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'search.modified.product.price',
            'views': [(view_form_id, 'form')],
            'view_id': view_form_id,
            'target': 'new',
        }

    # TODO
    def print_tags(self):
        print(self.product_ids.ids)

    date = fields.Datetime(string='Start Date', default=fields.Datetime.now(), required=True)
    product_ids = fields.Many2many('product.product', string="Products")