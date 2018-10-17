odoo.define('odoo_vendor_portal.take_price', function (require) {
'use strict';

    require('web.dom_ready');
    var webPortal = require('portal.portal');
    var ajax = require('web.ajax');

    $('#wksubmit').on("click", function(event){
        var offerNote = document.getElementById("inputNote").value;
        var userId = parseInt($('#loguser').val());
        var rfqId = parseInt($('#rfqId').val());
        ajax.jsonRpc("/update/vendorprice/", 'call', {
            'rfqId': rfqId, 'offerNote' : offerNote, 'vendorUserId' : userId})
        .then(function (vals){
            window.location.reload();
        });

    });

});
