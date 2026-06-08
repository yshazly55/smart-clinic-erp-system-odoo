A custom healthcare ERP module built on Odoo that eliminates manual chaos in clinical environments by automating the full patient care workflow.
🚀 Features

Auto Triage — Patients scored on arrival (Emergency: 100, Urgent: 60, Routine: 20) and queue sorted automatically
Smart Doctor Assignment — Least-busy doctor matched by specialization assigned in one click
Double-Booking Prevention — Hard Python constraint blocks overlapping appointments
Real-Time Supply Tracking — Medical inventory depletes on appointment completion with instant low-stock alerts
Calendar Integration — Every appointment synced to Odoo's Calendar module
Overdue Detection — Patients waiting beyond their priority limit flagged red automatically

🛠️ Odoo Modules Used
Employees (hr) Calendar Inventory / Stock Mail / Discuss Base
📁 Custom Models
ModelDescriptionclinic.patient.ticketPatient intake and triageclinic.appointmentAppointment scheduling and supply consumptionclinic.appointment.typeAppointment templates with required suppliesclinic.supplyMedical inventory with low-stock alertsclinic.supply.moveSupply consumption logs per appointment
⚙️ Installation

Copy the smart_clinic_ops folder into your Odoo addons directory
Enable Developer Mode in Odoo Settings
Go to Apps → Update Apps List
Search Smart Clinic and click Install

👥 Team
MMMY Team — Odoo Innovation Challenge 2025 | Technology & Innovation Track
