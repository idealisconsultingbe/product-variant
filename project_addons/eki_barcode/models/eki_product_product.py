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

from odoo import models, _


class EkiProductProduct(models.Model):
    _inherit = "product.product"

    def history_action(self):
        form_view_id = self.env.ref('eki_barcode.eki_product_lot_form_view').id
        tree_view_id = self.env.ref('eki_barcode.eki_product_lot_tree_view').id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Product History'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'eki.product.lot',
            'domain': str([('product_id', '=', self.id)]),
            'context': str({'default_product_id': self.id}),
            'target': 'current',
            'view_id': tree_view_id,
            'views': [[tree_view_id, "tree"], [form_view_id, "form"]]
        }
