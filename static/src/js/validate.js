odoo.define('purchase.validate', function (require) {
'use strict';

    require('web.dom_ready');
    var webPortal = require('portal.portal');
    var ajax = require('web.ajax');

    $('#wkvalidate').on("click", function(event){
        var userId = parseInt($('#loguser').val());
        var rfqId = parseInt($('#rfqId').val());

        ajax.jsonRpc("/update/validate/", 'call', {'rfqId': rfqId, 'vendorUserId' : userId})
        .then(function (vals){
            window.location.reload();
        });

    });

});
