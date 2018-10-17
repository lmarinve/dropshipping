# -*- coding: utf-8 -*-
##########################################################################
#
#   Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
#
##########################################################################

from odoo import api, fields, models, _


class VendorLoginAccount(models.TransientModel):
    _name = 'login.account'

    @api.multi
    def create_vendor_acocunt(self):
        self.ensure_one()
        ctx = dict(self.env.context or {})
        activeModel = ctx.get('active_model')
        activeId = ctx.get('active_id')
        if activeModel == 'res.partner':
            parnterObj = self.env['res.partner'].browse(activeId)
            userModel = self.env['res.users']
            if parnterObj.user_vendor:
                userModel.reset_password(parnterObj.email)
                userObj = userModel.sudo().search([('partner_id', '=', parnterObj.id)])
            else:
                vals = {
                    'partner_id' : ctx.get('active_id'),
                    'login' : parnterObj.email,
                    'email' : parnterObj.email,
                    'password' : parnterObj.email,
                    'groups_id' : [(5,)]
                    }
                userObj = userModel.create(vals)
                if userObj:
                    irModelData = self.env['ir.model.data']
                    templXmlId = irModelData.get_object_reference('base', 'group_portal')[1]
                    res = userObj.write({'groups_id': [(6, 0, [templXmlId])]})
                    parnterObj.user_vendor = True
                    #parnterObj.user_id = userObj.id
        return True
