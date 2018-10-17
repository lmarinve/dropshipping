odoo.define('purchase.validate_all', function (require) {
'use strict';

    require('web.dom_ready');
    var webPortal = require('portal.portal');
    var ajax = require('web.ajax');

    $('#wkvalidate_all').on("click", function(event){
        var orderId = parseInt($('#orderId').val());
        ajax.jsonRpc("/update/validate/all", 'call', {'orderId': orderId})
        .then(function (vals){
            window.location.reload();
        });

    });

});
