odoo.define('purchase.reject', function (require) {
'use strict';

    require('web.dom_ready');
    var webPortal = require('portal.portal');
    var ajax = require('web.ajax');

    $('#wkreject_all').on("click", function(event){
        var orderId = parseInt($('#orderId').val());
        var offerNote = document.getElementById("inputNote").value;
        ajax.jsonRpc("/update/reject/all", 'call', {'orderId': orderId, 'observ': offerNote})
        .then(function (vals){
            window.location.reload();
        });

    });

});
