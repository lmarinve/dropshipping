# -*- coding: utf-8 -*-
{
    'name': "Vendor Selection For Dropshipping",

    'summary': """
        Customer will select vendor as per his choice.""",

    'description': """
       Customer will select vendor as per his choice in sale order when customer choose drop shipping scenario.
    """,

    'author': "Luis Marin ",
    'website': "http://www.compushopservice.com/",

    
    'category': 'Sales',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['product', 'sale', 'sale_management', 'sale_stock', 'auth_signup','website_sale', 'purchase'],

    # always loaded
    'data': [
        'security/dropship_sale_order_security.xml',
        'views/login_account_view.xml',
        'views/res_partner_view.xml',
        'views/sale_order.xml',
        'views/portal_templates.xml',
        'views/purchase_views.xml',
        'report/dropship_portal_reports.xml',
        'report/dropship_portal_report_views.xml',
        'report/po_templates.xml',
        'report/pq_templates.xml',
        'data/purchase.yml',
        'data/mail_template_data.xml',
    ],
    

   'images':  ['static/description/banner.jpg'],
    'application': True,
}
