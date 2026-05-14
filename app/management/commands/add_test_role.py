"""
Management command to add test roles to users for testing multi-role functionality
"""
from django.core.management.base import BaseCommand
from app.models import User


class Command(BaseCommand):
    help = 'Add a second role to a user for testing multi-role functionality'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username of the user')
        parser.add_argument('role', type=str, help='Role to add (TENANT, LANDLORD, AGENT, SUPER_ADMIN)')

    def handle(self, *args, **options):
        username = options['username']
        role = options['role']
        
        # Validate role
        valid_roles = [r[0] for r in User.Role.choices]
        if role not in valid_roles:
            self.stdout.write(self.style.ERROR(f'Invalid role: {role}'))
            self.stdout.write(self.style.WARNING(f'Valid roles: {", ".join(valid_roles)}'))
            return
        
        # Get user
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User not found: {username}'))
            return
        
        # Add role
        if user.add_role(role):
            self.stdout.write(self.style.SUCCESS(f'Successfully added {role} role to {username}'))
            self.stdout.write(self.style.SUCCESS(f'User now has roles: {", ".join(user.roles)}'))
            self.stdout.write(self.style.SUCCESS(f'Active role: {user.active_role}'))
        else:
            self.stdout.write(self.style.WARNING(f'User already has {role} role'))
