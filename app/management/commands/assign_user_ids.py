from django.core.management.base import BaseCommand
from app.models import User
import random


class Command(BaseCommand):
    help = 'Assigns unique 4-digit IDs to existing users without user_id'

    def handle(self, *args, **kwargs):
        users_without_id = User.objects.filter(user_id__isnull=True)
        count = users_without_id.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('All users already have user IDs!'))
            return
        
        self.stdout.write(f'Found {count} users without user_id. Assigning...')
        
        updated = 0
        for user in users_without_id:
            # The save() method will automatically generate user_id
            user.save()
            updated += 1
            self.stdout.write(
                self.style.SUCCESS(f'✓ Assigned ID {user.user_id} to {user.username}')
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'\nSuccessfully assigned user IDs to {updated} users!')
        )
