"""Raw order evidence per case (synthetic). Unstructured on purpose:
this is what the model has to read and turn into typed flags."""

EVIDENCE = {
    "A": """\
ORDER HISTORY - customer j.marin@example.com
Order        Date        Amount    Device fingerprint   IP              Disputed
ORD-7781     2026-03-02  $  89.00  fp_8c21e9            82.77.14.203    no
ORD-8112     2026-05-17  $ 214.50  fp_8c21e9            82.77.14.203    no
ORD-8840     2026-07-29  $  56.20  fp_8c21e9            82.77.14.203    no
ORD-9013     2026-08-11  $  32.00  fp_41aa07            188.25.9.40     refunded
ORD-9902     2026-10-14  $1240.00  fp_8c21e9            82.77.14.203    <- this dispute

CARRIER (DHL) - ORD-9902
14 Oct 18:02  Out for delivery
14 Oct 19:47  Delivered. Signed by: J. MARIN. Signature image on file.
""",
    "B": """\
CARRIER (Posta) - ORD-9921, phone case, $18.00
16 Oct 09:12  Parcel accepted at depot
17 Oct 13:40  Delivered - left at front door. No signature required for this service.
No photo on file.
""",
    "C": """\
SUPPORT INBOX - ORD-9750, headphones, $340.00

From: a.popescu@example.com   Date: 02 Oct 2026
Subject: Return
Hi, I sent the headphones back today with the return label you emailed. Please refund.

From: a.popescu@example.com   Date: 09 Oct 2026
Subject: Re: Return
It's been a week and still no refund. Can someone please answer me??

(no replies sent from support@shop)

RETURNS SYSTEM - ORD-9750
Return label generated 01 Oct. Warehouse receipt: not recorded.
REFUNDS - ORD-9750: none issued.
""",
}
ORDER_FACTS = {
    "A": {
        "product_type": "PHYSICAL_GOODS",
        "order_info": {
            "id": "ORD-9902",
            "created_at": "2026-10-14T09:15:00+00:00",
            "total_amount": 1240.00,
            "total_currency": "USD",
            "products": [{"name": "Laptop", "quantity": 1, "unit_price": 1240.00,
                          "type": "physical_good"}],
        },
        "delivery_info": {
            "status": "DELIVERED",
            "shipping_company": "DHL",
            "tracking_number": "JD014600812345",
            "shipped_at": "2026-10-14T11:00:00+00:00",
            "delivered_at": "2026-10-14T16:47:00+00:00",
            "name": "J. MARIN",
        },
        "seller_info": {"name": "Demo Shop", "store_url": "https://shop.example.com"},
    },
}


# Who bought what: shown on approvals (counterparty + purchase terms).
ORDERS = {
    "A": {"customer": "j.marin@example.com",   "order_id": "ORD-9902", "product": "Laptop"},
    "B": {"customer": "b.ionescu@example.com", "order_id": "ORD-9921", "product": "Phone case"},
    "C": {"customer": "a.popescu@example.com", "order_id": "ORD-9750", "product": "Headphones"},
}