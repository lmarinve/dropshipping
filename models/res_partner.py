# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.base.res.res_partner import WARNING_MESSAGE, WARNING_HELP


class res_partner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    user_id = fields.Many2one('res.user', string='Portal User')
    user_vendor = fields.Boolean(default=False,string='Portal User')
    trusted_vendor = fields.Boolean(default=False,string='Trusted')
    vendor_password = fields.Char()
    supplierinfo_ids = fields.One2many('product.supplierinfo', 'name', string='Pricelists')
    
    @api.multi
    def act_show_supplierinfo(self):
        action = self.env.ref('product.product_supplierinfo_type_action')
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'view_type': action.view_type,
            'view_mode': action.view_mode,
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        result['domain'] = "[('id','in',["+','.join(map(str, self.supplierinfo_ids.ids))+"])]"
        return result
