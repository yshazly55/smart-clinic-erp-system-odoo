from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ClinicAppointment(models.Model):
    _name = "clinic.appointment"
    _description = "Clinic Appointment"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "start_datetime desc"

    name = fields.Char(compute="_compute_name", store=True)

    patient_ticket_id = fields.Many2one(
        "clinic.patient.ticket",
        string="Patient Ticket",
        required=True,
        ondelete="cascade",
    )
    patient_name = fields.Char(related="patient_ticket_id.patient_name", store=True)

    doctor_id = fields.Many2one(
        "hr.employee",
        required=True,
        domain="[('is_clinic_doctor', '=', True)]",
    )

    appointment_type_id = fields.Many2one("clinic.appointment.type", required=True)

    start_datetime = fields.Datetime(required=True)
    end_datetime = fields.Datetime(required=True)

    state = fields.Selection(
        [
            ("scheduled", "Scheduled"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        default="scheduled",
        tracking=True,
    )

    calendar_event_id = fields.Many2one("calendar.event", readonly=True)
    supply_move_ids = fields.One2many("clinic.supply.move", "appointment_id", string="Consumed Supplies")

    @api.depends("patient_ticket_id", "doctor_id", "start_datetime")
    def _compute_name(self):
        for appointment in self:
            patient = appointment.patient_ticket_id.patient_name or "Patient"
            doctor = appointment.doctor_id.name or "Doctor"
            appointment.name = f"{patient} with {doctor}"

    @api.constrains("doctor_id", "start_datetime", "end_datetime", "state")
    def _check_doctor_double_booking(self):
        """Block appointments where the same doctor is already booked."""
        for appointment in self:
            if not appointment.doctor_id or not appointment.start_datetime or not appointment.end_datetime:
                continue
            if appointment.start_datetime >= appointment.end_datetime:
                raise ValidationError("Appointment end time must be after start time.")

            overlap_count = self.search_count(
                [
                    ("id", "!=", appointment.id),
                    ("doctor_id", "=", appointment.doctor_id.id),
                    ("state", "=", "scheduled"),
                    ("start_datetime", "<", appointment.end_datetime),
                    ("end_datetime", ">", appointment.start_datetime),
                ]
            )
            if overlap_count:
                raise ValidationError("This doctor is already booked during this time. Double-booking is not allowed.")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._create_calendar_events()
        return records

    def _create_calendar_events(self):
        """Create a matching Calendar event for visual scheduling."""
        for appointment in self:
            if appointment.calendar_event_id:
                continue

            event = self.env["calendar.event"].create(
                {
                    "name": appointment.name,
                    "start": appointment.start_datetime,
                    "stop": appointment.end_datetime,
                    "allday": False,
                }
            )
            appointment.calendar_event_id = event.id

    def action_mark_done(self):
        """Finish the appointment and consume required medical supplies."""
        Move = self.env["clinic.supply.move"]

        for appointment in self:
            if appointment.state == "done":
                continue

            # First check all required supplies before subtracting anything.
            for line in appointment.appointment_type_id.supply_line_ids:
                if line.supply_id.qty_on_hand < line.quantity:
                    raise ValidationError(
                        f"Not enough stock for {line.supply_id.name}. "
                        f"Available: {line.supply_id.qty_on_hand}, Required: {line.quantity}"
                    )

            # Then subtract supplies and create consumption records.
            for line in appointment.appointment_type_id.supply_line_ids:
                supply = line.supply_id
                supply.qty_on_hand -= line.quantity

                Move.create(
                    {
                        "appointment_id": appointment.id,
                        "supply_id": supply.id,
                        "quantity": line.quantity,
                    }
                )

                if supply.low_stock:
                    supply.action_send_low_stock_email()

            appointment.state = "done"
            appointment.patient_ticket_id.state = "done"
            appointment.message_post(body="Appointment completed and medical supplies were consumed.")

    def action_cancel(self):
        for appointment in self:
            appointment.state = "cancelled"
            if appointment.calendar_event_id:
                appointment.calendar_event_id.unlink()


class ClinicSupplyMove(models.Model):
    _name = "clinic.supply.move"
    _description = "Clinic Supply Consumption Move"
    _order = "date desc"

    appointment_id = fields.Many2one("clinic.appointment", required=True, ondelete="cascade")
    supply_id = fields.Many2one("clinic.supply", required=True)
    quantity = fields.Float(required=True)
    date = fields.Datetime(default=fields.Datetime.now)
