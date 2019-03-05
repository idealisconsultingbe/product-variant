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


class EkiProductAllergens(models.Model):
    _name = "eki.product.allergens"
    _description = "Allergens on the product"

    name = fields.Char(string="Allergen name")


class EkiProductLabels(models.Model):
    _name = "eki.product.labels"
    _description = "Labels on the product"

    name = fields.Char(string="Label name")
    pictogram = fields.Binary("Pictogram", attachment=True, required=True)


class EkiProductCategory(models.Model):
    _inherit = "product.category"

    eki_is_price_change_continuously = fields.Boolean(string="Price change continuously")
    eki_is_return = fields.Boolean(string="Return")

    @api.onchange('parent_id')
    def _onchange_parent_id_eki_fields(self):
        if self.parent_id:
            self.eki_is_price_change_continuously = self.parent_id.eki_is_price_change_continuously
            self.eki_is_return = self.parent_id.eki_is_return

    @api.model
    def create(self, values):
        product_category = super(EkiProductCategory, self).create(values)
        if product_category.parent_id:
            product_category.write({
                'eki_is_price_change_continuously': product_category.parent_id.eki_is_price_change_continuously,
                'eki_is_return': product_category.parent_id.eki_is_return
            })
        return product_category

    @api.multi
    def write(self, values):
        res = super(EkiProductCategory, self).write(values)
        if not self.parent_id and 'eki_is_price_change_continuously' in values or 'eki_is_return' in values:
            product_category_ids = self.search([('parent_id', '=', self.id)])
            for product_category_id in product_category_ids:
                product_category_id.write({
                    'eki_is_price_change_continuously': self.eki_is_price_change_continuously,
                    'eki_is_return': self.eki_is_return
                })
        return res


class EkiProductTemplate(models.Model):
    _inherit = "product.template"

    eki_brand = fields.Char(string="Brand")
    eki_packaging = fields.Char(string="Packaging")
    eki_ingredient = fields.Char(string="Ingredient")
    eki_conservation = fields.Char(string="Conservation")
    eki_use = fields.Char(string="Utilisation")
    eki_supplier_information = fields.Char(string="Supplier Information")
    eki_nutritional_values = fields.Char(string="Nutritional Values")
    eki_nutritional_advise = fields.Char(string="Nutritional advise")
    eki_internal_notes = fields.Char(string="Internal Notes")
    eki_ldap = fields.Integer(string="Limit date after purchase")
    eki_product_allergens_ids = fields.Many2many('eki.product.allergens', 'eki_product_allergens_product_template_rel', 'product_id', 'product_allergen_id', string="Allergens")
    eki_product_labels_ids = fields.Many2many('eki.product.labels', 'eki_product_labels_product_template_rel', 'product_id', 'product_label_id', string="Labels")

    eki_is_tactile_sale = fields.Boolean(string="Is for tactile sale")
    eki_has_tare = fields.Boolean(string="Has tare")
    eki_available_on_pos_caterer = fields.Boolean(string="Available on PoS caterer")

    eki_is_return = fields.Boolean(string="Returns", related="categ_id.eki_is_return", readonly=True)

    eki_return = fields.Many2one('product.product', domain=[('eki_is_return', '=', True)])

