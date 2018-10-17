# -*- coding: utf-8 -*-
##########################################################################
#
#   Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
#
##########################################################################
import base64
import werkzeug
import werkzeug.urls
import hashlib

from collections import OrderedDict

from odoo import http, SUPERUSER_ID, _
from odoo.http import Controller, request, route
from odoo.addons.web.controllers.main import WebClient
from odoo.exceptions import AccessError, ValidationError

from odoo import tools
from odoo.tools.translate import _

from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager, get_records_pager

import logging
_logger = logging.getLogger(__name__)

class CustomerPortal(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super(CustomerPortal, self)._prepare_portal_layout_values()
        _logger.debug("*********** 1.- ok main.py _prepare_portal_layout_values values: %r", values)
        _logger.debug("*********** end _prepare_portal_layout_values ************")
        partner = request.env.user.partner_id

        _logger.debug("*********** 1.- main.py _prepare_portal_layout_values request.env.user: %r", request.env.user)
        _logger.debug("*********** end _prepare_portal_layout_values ************")

        _logger.debug("*********** 1.- main.py _prepare_portal_layout_values partner: %r", partner)
        _logger.debug("*********** end _prepare_portal_layout_values ************")
		
        vendorPO = request.env['purchase.order'].sudo()
        _logger.debug("*********** 1.- main.py _prepare_portal_layout_values vendorPO: %r", vendorPO)
        _logger.debug("*********** end _prepare_portal_layout_values ************")

        poCount = vendorPO.search_count([('partner_id', '=', [partner.id])])

        _logger.debug("*********** 1.- main.py _prepare_portal_layout_values poCount: %r", poCount)
        values.update({'purchase_count': poCount})
        _logger.debug("*********** end _prepare_portal_layout_values ************")
        return values

	
    @http.route(['/my/purchase', '/my/purchase/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_purchase_orders(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        _logger.debug("***********  8.- portal_my_purchase_orders on dropship_portal controller ************")

        values = self._prepare_portal_layout_values()

        _logger.debug("*********** 8.- /web/purchase', '/web/purchase/page/<int:page> values: %r", values)
        _logger.debug("*********** 8.- /web/purchase', '/web/purchase/page/<int:page> end values ************")

        partner = request.env.user.partner_id

        _logger.debug("*********** 8.- /web/purchase', '/web/purchase/page/<int:page> partner: %r", partner)
        _logger.debug("*********** 8.- /web/purchase', '/web/purchase/page/<int:page> end partner ************")

        PurchaseOrder = request.env['purchase.order']

        _logger.debug("*********** 8.- /web/purchase', '/web/purchase/page/<int:page> purchase order: %r", PurchaseOrder)
        _logger.debug("*********** 8.- /web/purchase', '/web/purchase/page/<int:page> end purchase order ************")

        domain = [
            '|',
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('partner_id', 'child_of', [partner.commercial_partner_id.id]),
        ]

        archive_groups = self._get_archive_groups('purchase.order', domain)

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        searchbar_sortings = {
            'status': {'label': _('Status'), 'order': 'state desc, id desc'},
            'date': {'label': _('Newest'), 'order': 'create_date desc, id desc'},
            'name': {'label': _('Order'), 'order': 'name asc, id asc'},
        }

        _logger.debug("*********** 8.- /web/purchase', '/web/purchase/page/<int:page> searchbar_sortings: %r", searchbar_sortings)
        _logger.debug("*********** 8.- /web/purchase', '/web/purchase/page/<int:page> end searchbar_sortings ************")

        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        _logger.debug("*********** 8.- /web/purchase', '/web/purchase/page/<int:page> order: %r", order)
        _logger.debug("*********** 8.- /web/purchase', '/web/purchase/page/<int:page> end order ************")
  
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': [('state', 'in', ['draft','purchase', 'sent', 'done', 'cancel'])]},
            'draft': {'label': _('No Assigned'), 'domain': [('state', '=', 'draft')]},
            'purchase': {'label': _('Purchase Order'), 'domain': [('state', '=', 'purchase')]},
            'sent': {'label': _('Pending'), 'domain': [('state', '=', 'sent')]},
            'cancel': {'label': _('Cancelled'), 'domain': [('state', '=', 'cancel')]},
            'done': {'label': _('Locked'), 'domain': [('state', '=', 'done')]},
        }

        _logger.debug("*********** 8.- /web/purchase', '/web/purchase/page/<int:page> searchbar_filters: %r", searchbar_filters)
        _logger.debug("*********** 8.- /web/purchase', '/web/purchase/page/<int:page> end searchbar_filters ************")

        # default filter by value
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        _logger.debug("*********** 8.- /web/purchase', '/web/purchase/page/<int:page> domain: %r", domain)
        _logger.debug("*********** 8.- /web/purchase', '/web/purchase/page/<int:page> end domain ************")

        # count for pager
        purchase_count = PurchaseOrder.search_count(domain)
        # make pager
        pager = portal_pager(
            url="/my/purchase",
            url_args={'date_begin': date_begin, 'date_end': date_end},
            total=purchase_count,
            page=page,
            step=self._items_per_page
        )
        # search the purchase orders to display, according to the pager data
        orders = PurchaseOrder.search(
            domain,
            order=order,
            limit=self._items_per_page,
            offset=pager['offset']
        )

        _logger.debug("*********** 8.- /web/purchase', '/web/purchase/page/<int:page> order 4: %r", order)
        _logger.debug("*********** 8.- /web/purchase', '/web/purchase/page/<int:page> end order 4 ************")

        request.session['my_purchases_history'] = orders.ids[:100]

        values.update({
            'date': date_begin,
            'orders': orders,
            'page_name': 'purchase',
            'pager': pager,
            'archive_groups': archive_groups,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
            'default_url': '/my/purchase',
        })

        _logger.debug("*********** 8.- /web/purchase', '/web/purchase/page/<int:page> values4: %r", values)
        _logger.debug("*********** 8.- /web/purchase', '/web/purchase/page/<int:page> end values 4 ************")

        return request.render("dropship_portal.portal_my_purchase_orders", values)
		
    @http.route(['/web/3QI6I5o5fJTW2oCzivoK/<int:order>'], type='http', auth="public", website=True)
    def portal_my_po(self, order=None, access_token=None, **kw):

        orderObj = request.env['purchase.order'].browse(order)
        try:
            orderObj.check_access_rights('read')
            orderObj.check_access_rule('read')
        except AccessError:
            return request.redirect('/web')
        _logger.debug("*********** z.- /web/purchase/<int:order_id> order: %r", order)
        _logger.debug("*********** z.- end /web/purchase/<int:order_id> order ************")

        history = request.session.get('my_purchases_history', [])
        customer = request.env.user.partner_id.id
        _logger.debug("*********** z.- /web/purchase/<int:order_id> customer: %r", customer)

        values = {}
        values.update(customer_id=customer,order= orderObj.sudo())
        customer_data = request.env['res.partner'].sudo().browse(customer)
        values.update(partner_name=customer_data.name, partner_mail=customer_data.email, partner_id=customer)

        values.update(get_records_pager(history, orderObj))

        _logger.debug("*********** z.- /web/purchase/<int:order_id> values: %r", values)
        _logger.debug("*********** z.- /web/purchase/<int:order_id> end values ************")

        return request.render("dropship_portal.portal_my_purchase_order", values)

    @http.route(['/my/purchase/<int:order_id>'], type='http', auth="public", website=True)
    def portal_my_purchase_order(self, order_id=None, **kw):

        _logger.debug("*********** 9.- /web/purchase/<int:order_id> order_id: %r", order_id)
        _logger.debug("*********** 9.- /web/purchase/<int:order_id> kw: %r", kw)
        order = request.env['purchase.order'].browse(order_id)
        poOrder = order.id
        _logger.debug("*********** 9.- /web/purchase/<int:order_id> order: %r", order)
        _logger.debug("*********** 9.- end /web/purchase/<int:order_id> order ************")

        try:
            order.check_access_rights('read')
            order.check_access_rule('read')
        except AccessError:
            return request.redirect('/my')

        history = request.session.get('my_purchases_history', [])
        #customer = request.env.user.partner_id.id
        customer = order.user_id.partner_id.id

        values = {}
        _logger.debug("*********** 9.- /web/purchase/<int:order_id> kw: %r", kw)
        _logger.debug("*********** 9.- /web/purchase/<int:order_id> end kwargs ************")
        _logger.debug("*********** 9.- /web/purchase/<int:order_id> customer: %r", customer)
        for field in ['prq_1','prq_2','prq_3','prq_4','prq_5','prq_6','prq_7','prq_8','prq_9','prq_10',
                      'desc_1','desc_2','desc_3','desc_4','desc_5','desc_6','desc_7','desc_8','desc_9','desc_10',
                      'rejx_1','rejx_2','rejx_3','rejx_4','rejx_5','rejx_6','rejx_7','rejx_8','rejx_9','rejx_10']:
            if kw.get(field):
                values[field] = kw.pop(field)
        values.update(kwargs=kw.items())
        values.update(customer_id=customer,order= order.sudo())
        customer_data = request.env['res.partner'].sudo().browse(customer)
        values.update(partner_name=customer_data.name, partner_mail=customer_data.email, partner_id=customer)
        values.update(get_records_pager(history, order))

        _logger.debug("*********** 9.- /web/purchase/<int:order_id> values: %r", values)
        _logger.debug("*********** 9.- /web/purchase/<int:order_id> end values ************")

        return request.render("dropship_portal.portal_my_purchase_order", values)

    @http.route(['/update/validate/all'], type='json', auth="user", methods=['POST'] , website=True)
    def update_validate_all(self, orderId):
        context, env = request.context, request.env
        currentLogUser = request.env.user
        vendor = currentLogUser.partner_id.name
        poModel = env['purchase.order']
        po_Obj = poModel.sudo().browse(orderId)
        _logger.debug("*********** 6.- main.py /update/validate/all **********")
        _logger.debug("*********** 6.- main.py /update/validate/all po_Obj: %r", po_Obj)
        _logger.debug("*********** 6.- main.py /update/validate/all vendor: %r", vendor)
        notes = "VALIDATED by " + vendor
        po_Obj.write({'state': 'purchase'})
        for pLine in po_Obj.order_line:
            sLine = pLine.sale_line.id
            if sLine:
                saleLineObj = env['sale.order.line'].sudo().browse(sLine)
                if saleLineObj:
                    saleLineObj.write({'item_status' : 'OD'})
        return True

    @http.route(['/update/reject/all'], type='json', auth="user", methods=['POST'] , website=True)
    def update_reject_all(self, orderId, observ):
        context, env = request.context, request.env
        currentLogUser = request.env.user
        vendor = currentLogUser.partner_id.name
        poModel = env['purchase.order']
        po_Obj = poModel.sudo().browse(orderId)
        _logger.debug("*********** 7.- main.py /update/reject/all **********")
        _logger.debug("*********** 7.- main.py /update/reject/all **********")
        _logger.debug("*********** 7.- main.py /update/reject/all **********")
        _logger.debug("*********** 7.- main.py /update/reject/all vendor: %r", vendor)
        notes = "Rejected by " + vendor + ": " + observ
        po_Obj.write({'state': 'draft', 'observ': notes})
        for pLine in po_Obj.order_line:
            sLine = pLine.sale_line.id
            if sLine:
                saleLineObj = env['sale.order.line'].sudo().browse(sLine)
                if saleLineObj:
                    saleLineObj.write({'item_status' : 'QO'})
        return True
