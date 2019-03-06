# Copyright 2016 Sergio Teruel <sergio.teruel@tecnativa.com>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _update_fix_price(self, vals):
        if 'list_price' in vals:
            self.mapped('product_variant_ids').write({
                'fix_price': vals['list_price']})

    @api.model
    def create(self, vals):
        product_tmpl = super(ProductTemplate, self).create(vals)
        product_tmpl._update_fix_price(vals)
        return product_tmpl

    @api.multi
    def write(self, vals):
        res = super(ProductTemplate, self).write(vals)
        for template in self:
            if not self.env.context.get('skip_update_fix_price', False):
                template._update_fix_price(vals)
        return res


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.multi
    @api.depends('fix_price')
    def _compute_lst_price(self):
        for product in self:
            product.lst_price = product.fix_price or product.list_price

    @api.multi
    def _compute_list_price(self):
        for product in self:
            product.list_price = product.fix_price or product.product_tmpl_id.list_price

    @api.multi
    def _inverse_product_lst_price(self):
        for product in self:
            vals = {}
            vals['fix_price'] = product.lst_price
            if product.product_variant_count == 1:
                product.product_tmpl_id.list_price = vals['fix_price']
            else:
                fix_prices = product.product_tmpl_id.mapped(
                    'product_variant_ids.fix_price')
                # for consistency with price shown in the shop
                product.product_tmpl_id.with_context(
                    skip_update_fix_price=True).list_price = min(fix_prices)
            product.write(vals)

    lst_price = fields.Float(
        compute='_compute_lst_price',
        inverse='_inverse_product_lst_price',
    )
    list_price = fields.Float(
        compute='_compute_list_price',
    )
    fix_price = fields.Float(string='Fix Price')
