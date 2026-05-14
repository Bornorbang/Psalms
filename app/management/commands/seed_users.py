from django.core.management.base import BaseCommand
from app.models import User


class Command(BaseCommand):
    help = 'Seeds the database with test users for each role'

    def handle(self, *args, **kwargs):
        # Test users data
        test_users = [
            {
                'username': 'tenant_user',
                'email': 'tenant@test.com',
                'password': 'test123',
                'first_name': 'John',
                'last_name': 'Tenant',
                'role': User.Role.TENANT,
                'phone_number': '+1234567890',
            },
            {
                'username': 'landlord_user',
                'email': 'landlord@test.com',
                'password': 'test123',
                'first_name': 'Sarah',
                'last_name': 'Landlord',
                'role': User.Role.LANDLORD,
                'phone_number': '+1234567891',
            },
            {
                'username': 'agent_user',
                'email': 'agent@test.com',
                'password': 'test123',
                'first_name': 'Mike',
                'last_name': 'Agent',
                'role': User.Role.AGENT,
                'phone_number': '+1234567892',
            },
        ]

        created_count = 0
        for user_data in test_users:
            username = user_data['username']
            
            # Check if user already exists
            if User.objects.filter(username=username).exists():
                self.stdout.write(
                    self.style.WARNING(f'User "{username}" already exists, skipping...')
                )
                continue
            
            # Create user
            password = user_data.pop('password')
            user = User.objects.create_user(**user_data)
            user.set_password(password)
            user.email_verified = True  # Pre-verify for testing
            user.save()
            
            created_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f'Created {user.get_role_display()} user: {username} (password: test123)'
                )
            )

        if created_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'\nSuccessfully created {created_count} test user(s)')
            )
        else:
            self.stdout.write(
                self.style.WARNING('\nNo new users were created')
            )
        
        # Display all users
        self.stdout.write('\n' + '='*60)
        self.stdout.write('EXISTING USERS IN DATABASE:')
        self.stdout.write('='*60)
        for user in User.objects.all().order_by('role', 'username'):
            self.stdout.write(
                f'{user.username:20} | {user.email:25} | {user.get_role_display()}'
            )
