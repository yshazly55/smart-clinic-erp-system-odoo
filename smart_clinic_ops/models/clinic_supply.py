from odoo import api, fields, models


class ClinicSupply(models.Model):
    _name = "clinic.supply"
    _description = "Clinic Medical Supply"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True, tracking=True)
    qty_on_hand = fields.Float(string="Quantity On Hand", default=0, tracking=True)
    min_qty = fields.Float(string="Minimum Quantity", default=5, tracking=True)

    low_stock = fields.Boolean(
        string="Low Stock",
        compute="_compute_low_stock",
        store=True,
    )

    @api.depends("qty_on_hand", "min_qty")
    def _compute_low_stock(self):
        """Low stock becomes True when quantity reaches or goes below minimum."""
        for supply in self:
            supply.low_stock = supply.qty_on_hand <= supply.min_qty

    def action_send_low_stock_email(self):
        """Create/send an email alert for low stock.

        Note: In a local Odoo server, the email will only actually leave Odoo
        if an outgoing mail server is configured. Otherwise, it can still appear
        in the mail queue/logs for demo purposes.
        """
        for supply in self:
            subject = f"Critical Low Stock Alert: {supply.name}"
            body = f"""
                <p><b>Critical Low Stock Alert</b></p>
                <p>Supply: {supply.name}</p>
                <p>Quantity on hand: {supply.qty_on_hand}</p>
                <p>Minimum quantity: {supply.min_qty}</p>
            """

            # Pick the current user's email first, then company email.
            email_to = self.env.user.email or self.env.company.email

            # Always post a message in the record chatter so the alert is visible.
            supply.message_post(body=body, subject=subject)

            if email_to:
                mail = self.env["mail.mail"].create(
                    {
                        "subject": subject,
                        "body_html": body,
                        "email_to": email_to,
                    }
                )
                try:
                    mail.send()
                except Exception as error:
                    # Local Odoo often has no outgoing mail server configured.
                    # Keep the alert visible in chatter instead of crashing the demo.
                    supply.message_post(body=f"Email alert was created, but local sending failed: {error}")
