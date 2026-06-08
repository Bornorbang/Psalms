"""
Management command: check_overdue_rents

Marks overdue invoices and sends email notifications:
  - Invoices past their due date → status set to OVERDUE
  - Overdue tenants → email alert
  - Invoices due within 3 days → reminder email

Run daily via cron/scheduler:
    python manage.py check_overdue_rents
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta

from app.models import Invoice


class Command(BaseCommand):
    help = 'Mark overdue invoices and send payment reminder emails'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making DB changes or sending emails',
        )
        parser.add_argument(
            '--reminder-days',
            type=int,
            default=3,
            help='Days before due date to send reminder (default: 3)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        reminder_days = options['reminder_days']
        today = timezone.now().date()

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no changes will be saved.'))

        # ── 1. Mark SENT invoices as OVERDUE ────────────────────────────────
        overdue_qs = Invoice.objects.filter(
            status=Invoice.InvoiceStatus.SENT,
            due_date__lt=today,
        )
        overdue_count = overdue_qs.count()

        if not dry_run:
            overdue_qs.update(status=Invoice.InvoiceStatus.OVERDUE)

        self.stdout.write(f'Marked {overdue_count} invoice(s) as OVERDUE.')

        # ── 2. Send overdue notification emails ──────────────────────────────
        overdue_invoices = Invoice.objects.filter(
            status=Invoice.InvoiceStatus.OVERDUE,
        ).select_related(
            'tenant',
            'rental_agreement',
            'rental_agreement__rental_property',
            'rental_agreement__landlord',
        )

        notified_tenants = 0
        for invoice in overdue_invoices:
            days_overdue = (today - invoice.due_date).days
            tenant = invoice.tenant
            property_title = invoice.rental_agreement.rental_property.title

            if not dry_run:
                send_mail(
                    subject=f'Action Required: Overdue Rent – {property_title}',
                    message=(
                        f'Hi {tenant.first_name},\n\n'
                        f'Your rent payment is {days_overdue} day(s) overdue.\n\n'
                        f'Invoice:    {invoice.invoice_number}\n'
                        f'Amount Due: {invoice.currency} {invoice.balance:,.2f}\n'
                        f'Due Date:   {invoice.due_date.strftime("%d %b %Y")}\n'
                        f'Property:   {property_title}\n\n'
                        f'Please log in to your dashboard and make payment immediately '
                        f'to avoid further penalties.\n\n'
                        f'Psalms Real Estate'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[tenant.email],
                    fail_silently=True,
                )

                # Also notify landlord
                landlord = invoice.rental_agreement.landlord
                send_mail(
                    subject=f'Overdue Rent Alert – {property_title}',
                    message=(
                        f'Hi {landlord.first_name},\n\n'
                        f'The following tenant has an overdue payment for {property_title}.\n\n'
                        f'Tenant:     {tenant.get_full_name()}\n'
                        f'Invoice:    {invoice.invoice_number}\n'
                        f'Amount Due: {invoice.currency} {invoice.balance:,.2f}\n'
                        f'Days Overdue: {days_overdue}\n\n'
                        f'Psalms Real Estate'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[landlord.email],
                    fail_silently=True,
                )

            notified_tenants += 1

        self.stdout.write(f'Sent overdue alerts for {notified_tenants} invoice(s).')

        # ── 3. Send due-date reminder emails ────────────────────────────────
        reminder_date = today + timedelta(days=reminder_days)
        due_soon = Invoice.objects.filter(
            status=Invoice.InvoiceStatus.SENT,
            due_date=reminder_date,
        ).select_related(
            'tenant',
            'rental_agreement',
            'rental_agreement__rental_property',
        )

        reminders_sent = 0
        for invoice in due_soon:
            tenant = invoice.tenant
            property_title = invoice.rental_agreement.rental_property.title

            if not dry_run:
                send_mail(
                    subject=f'Rent Due in {reminder_days} Days – {property_title}',
                    message=(
                        f'Hi {tenant.first_name},\n\n'
                        f'This is a reminder that your rent payment is due in '
                        f'{reminder_days} day(s).\n\n'
                        f'Invoice:   {invoice.invoice_number}\n'
                        f'Amount:    {invoice.currency} {invoice.amount:,.2f}\n'
                        f'Due Date:  {invoice.due_date.strftime("%d %b %Y")}\n'
                        f'Property:  {property_title}\n\n'
                        f'Log in to your dashboard to pay now.\n\n'
                        f'Psalms Real Estate'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[tenant.email],
                    fail_silently=True,
                )
            reminders_sent += 1

        self.stdout.write(f'Sent {reminders_sent} due-date reminder(s) ({reminder_days} days out).')
        self.stdout.write(self.style.SUCCESS('Done.'))
