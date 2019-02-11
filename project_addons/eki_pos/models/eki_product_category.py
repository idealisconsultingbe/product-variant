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

from odoo import models, fields, api


class EkiProductCategory(models.Model):
    _inherit = 'product.category'

    pos_categ_id = fields.Many2one('pos.category', string='PoS Category')

    @api.model
    def create(self, vals_list):
        categ = super(EkiProductCategory, self).create(vals_list)

        pos_categ_obj = self.env['pos.category']

        sync_pos_categ = pos_categ_obj.create({
            'name': categ.name,
            'parent_id': categ.pos_categ_id.parent_id.id,
        })
        categ.pos_categ_id = sync_pos_categ

        return categ

    @api.multi
    def write(self, vals):
        result = super(EkiProductCategory, self).write(vals)
        for categ in self:
            categ.sync_pos_categ()
        return result

    @api.multi
    def unlink(self):
        for categ in self:
            categ.pos_categ_id.unlink()
        return super(EkiProductCategory, self).unlink()

    @api.one
    def sync_pos_categ(self):
        if self.pos_categ_id:
            self.pos_categ_id.name = self.name
            self.pos_categ_id.parent_id = self.parent_id.pos_categ_id
