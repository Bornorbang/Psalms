"""
Management command to seed sample properties for demo
Usage: python manage.py seed_properties
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from app.models import User, Property, Amenity, PropertyAmenity
from decimal import Decimal
import random

class Command(BaseCommand):
    help = 'Seed database with sample properties for Sprint 1 demo'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding properties...')
        
        # Get users for property assignment
        try:
            landlord = User.objects.filter(role='LANDLORD').first()
            agent = User.objects.filter(role='AGENT').first()
            
            if not landlord:
                self.stdout.write(self.style.ERROR('No landlord user found. Please create one first.'))
                return
            
            # Create amenities
            amenities_data = [
                {'name': 'Air Conditioning', 'icon': 'ac', 'category': 'Comfort'},
                {'name': 'Swimming Pool', 'icon': 'pool', 'category': 'Recreation'},
                {'name': 'Parking', 'icon': 'parking', 'category': 'Facilities'},
                {'name': 'Gym', 'icon': 'gym', 'category': 'Recreation'},
                {'name': 'Security', 'icon': 'security', 'category': 'Safety'},
                {'name': 'Garden', 'icon': 'garden', 'category': 'Outdoor'},
                {'name': 'Balcony', 'icon': 'balcony', 'category': 'Outdoor'},
                {'name': 'Elevator', 'icon': 'elevator', 'category': 'Facilities'},
                {'name': 'WiFi', 'icon': 'wifi', 'category': 'Technology'},
                {'name': 'Pet Friendly', 'icon': 'pet', 'category': 'Policy'},
            ]
            
            amenities = []
            for amenity_data in amenities_data:
                amenity, created = Amenity.objects.get_or_create(
                    name=amenity_data['name'],
                    defaults={'icon': amenity_data['icon'], 'category': amenity_data['category']}
                )
                amenities.append(amenity)
                if created:
                    self.stdout.write(f'  Created amenity: {amenity.name}')
            
            # Sample properties data
            properties_data = [
                {
                    'title': 'Modern Luxury Apartment in Downtown',
                    'description': 'Beautiful modern apartment with stunning city views. Features include hardwood floors, stainless steel appliances, and floor-to-ceiling windows.',
                    'property_type': 'APARTMENT',
                    'listing_type': 'RENT',
                    'status': 'AVAILABLE',
                    'price': Decimal('2500.00'),
                    'currency': 'USD',
                    'address': '123 Main Street',
                    'city': 'New York',
                    'state': 'NY',
                    'country': 'USA',
                    'postal_code': '10001',
                    'bedrooms': 2,
                    'bathrooms': Decimal('2.0'),
                    'living_area': Decimal('1200.00'),
                    'total_area': Decimal('1500.00'),
                    'floors': 15,
                    'year_built': 2020,
                    'garages': 1,
                    'is_featured': True,
                },
                {
                    'title': 'Spacious Family House with Garden',
                    'description': 'Perfect family home with large backyard and modern amenities. Quiet neighborhood with excellent schools nearby.',
                    'property_type': 'HOUSE',
                    'listing_type': 'SALE',
                    'status': 'AVAILABLE',
                    'price': Decimal('450000.00'),
                    'currency': 'USD',
                    'address': '456 Oak Avenue',
                    'city': 'Los Angeles',
                    'state': 'CA',
                    'country': 'USA',
                    'postal_code': '90001',
                    'bedrooms': 4,
                    'bathrooms': Decimal('3.0'),
                    'living_area': Decimal('2500.00'),
                    'total_area': Decimal('3500.00'),
                    'floors': 2,
                    'year_built': 2018,
                    'garages': 2,
                    'is_featured': True,
                },
                {
                    'title': 'Elegant Villa with Sea View',
                    'description': 'Stunning luxury villa overlooking the ocean. Private pool, spacious terraces, and premium finishes throughout.',
                    'property_type': 'VILLA',
                    'listing_type': 'SALE',
                    'status': 'AVAILABLE',
                    'price': Decimal('1200000.00'),
                    'currency': 'USD',
                    'address': '789 Coastal Drive',
                    'city': 'Miami',
                    'state': 'FL',
                    'country': 'USA',
                    'postal_code': '33101',
                    'bedrooms': 5,
                    'bathrooms': Decimal('4.5'),
                    'living_area': Decimal('4500.00'),
                    'total_area': Decimal('6000.00'),
                    'floors': 2,
                    'year_built': 2021,
                    'garages': 3,
                    'is_featured': True,
                },
                {
                    'title': 'Prime Commercial Office Space',
                    'description': 'Modern office space in business district. Ready for immediate occupancy with high-speed internet and parking.',
                    'property_type': 'OFFICE',
                    'listing_type': 'RENT',
                    'status': 'AVAILABLE',
                    'price': Decimal('5000.00'),
                    'currency': 'USD',
                    'address': '321 Business Blvd',
                    'city': 'Chicago',
                    'state': 'IL',
                    'country': 'USA',
                    'postal_code': '60601',
                    'bedrooms': 0,
                    'bathrooms': Decimal('2.0'),
                    'living_area': Decimal('3000.00'),
                    'total_area': Decimal('3500.00'),
                    'floors': 10,
                    'year_built': 2019,
                    'garages': 5,
                    'is_featured': False,
                },
                {
                    'title': 'Cozy Studio Apartment',
                    'description': 'Perfect for singles or couples. Efficient layout with modern amenities and great location near transit.',
                    'property_type': 'APARTMENT',
                    'listing_type': 'RENT',
                    'status': 'AVAILABLE',
                    'price': Decimal('1200.00'),
                    'currency': 'USD',
                    'address': '555 Student Lane',
                    'city': 'Boston',
                    'state': 'MA',
                    'country': 'USA',
                    'postal_code': '02101',
                    'bedrooms': 0,
                    'bathrooms': Decimal('1.0'),
                    'living_area': Decimal('500.00'),
                    'total_area': Decimal('550.00'),
                    'floors': 5,
                    'year_built': 2017,
                    'garages': 0,
                    'is_featured': False,
                },
                {
                    'title': 'Retail Shop in Shopping District',
                    'description': 'High foot traffic location perfect for retail business. Large display windows and storage area included.',
                    'property_type': 'SHOP',
                    'listing_type': 'RENT',
                    'status': 'AVAILABLE',
                    'price': Decimal('3500.00'),
                    'currency': 'USD',
                    'address': '888 Shopping Plaza',
                    'city': 'San Francisco',
                    'state': 'CA',
                    'country': 'USA',
                    'postal_code': '94101',
                    'bedrooms': 0,
                    'bathrooms': Decimal('1.0'),
                    'living_area': Decimal('1500.00'),
                    'total_area': Decimal('1800.00'),
                    'floors': 1,
                    'year_built': 2016,
                    'garages': 0,
                    'is_featured': False,
                },
                {
                    'title': 'Large Industrial Warehouse',
                    'description': 'Spacious warehouse with loading docks and office space. Ideal for distribution or manufacturing.',
                    'property_type': 'WAREHOUSE',
                    'listing_type': 'RENT',
                    'status': 'AVAILABLE',
                    'price': Decimal('8000.00'),
                    'currency': 'USD',
                    'address': '999 Industrial Way',
                    'city': 'Houston',
                    'state': 'TX',
                    'country': 'USA',
                    'postal_code': '77001',
                    'bedrooms': 0,
                    'bathrooms': Decimal('2.0'),
                    'living_area': Decimal('10000.00'),
                    'total_area': Decimal('12000.00'),
                    'floors': 1,
                    'year_built': 2015,
                    'garages': 10,
                    'is_featured': False,
                },
                {
                    'title': 'Prime Development Land',
                    'description': 'Excellent opportunity for developers. Zoned for residential or mixed-use development.',
                    'property_type': 'LAND',
                    'listing_type': 'SALE',
                    'status': 'AVAILABLE',
                    'price': Decimal('500000.00'),
                    'currency': 'USD',
                    'address': 'Lot 45 Development Road',
                    'city': 'Austin',
                    'state': 'TX',
                    'country': 'USA',
                    'postal_code': '78701',
                    'bedrooms': 0,
                    'bathrooms': Decimal('0.0'),
                    'living_area': Decimal('0.00'),
                    'total_area': Decimal('50000.00'),
                    'floors': 0,
                    'year_built': None,
                    'garages': 0,
                    'is_featured': False,
                },
                {
                    'title': 'Penthouse with Panoramic Views',
                    'description': 'Luxury penthouse with 360-degree city views. Premium finishes, private elevator access, and rooftop terrace.',
                    'property_type': 'APARTMENT',
                    'listing_type': 'SALE',
                    'status': 'AVAILABLE',
                    'price': Decimal('2500000.00'),
                    'currency': 'USD',
                    'address': '777 Skyline Tower',
                    'city': 'New York',
                    'state': 'NY',
                    'country': 'USA',
                    'postal_code': '10002',
                    'bedrooms': 3,
                    'bathrooms': Decimal('3.5'),
                    'living_area': Decimal('3500.00'),
                    'total_area': Decimal('4500.00'),
                    'floors': 40,
                    'year_built': 2022,
                    'garages': 2,
                    'is_featured': True,
                },
                {
                    'title': 'Charming Suburban House',
                    'description': 'Well-maintained family home in quiet neighborhood. Recently renovated kitchen and bathrooms.',
                    'property_type': 'HOUSE',
                    'listing_type': 'RENT',
                    'status': 'AVAILABLE',
                    'price': Decimal('2800.00'),
                    'currency': 'USD',
                    'address': '234 Maple Street',
                    'city': 'Seattle',
                    'state': 'WA',
                    'country': 'USA',
                    'postal_code': '98101',
                    'bedrooms': 3,
                    'bathrooms': Decimal('2.5'),
                    'living_area': Decimal('1800.00'),
                    'total_area': Decimal('2200.00'),
                    'floors': 2,
                    'year_built': 2010,
                    'garages': 2,
                    'is_featured': False,
                },
            ]
            
            # Create properties
            created_count = 0
            for prop_data in properties_data:
                # Check if property already exists
                if Property.objects.filter(title=prop_data['title']).exists():
                    self.stdout.write(f'  Property already exists: {prop_data["title"]}')
                    continue
                
                # Create property
                property_obj = Property.objects.create(
                    landlord=landlord,
                    agent=agent if agent else None,
                    **prop_data
                )
                
                # Add random amenities (3-6 amenities per property)
                num_amenities = random.randint(3, 6)
                selected_amenities = random.sample(amenities, num_amenities)
                
                for amenity in selected_amenities:
                    PropertyAmenity.objects.create(
                        property=property_obj,
                        amenity=amenity
                    )
                
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created: {property_obj.title}'))
            
            self.stdout.write(self.style.SUCCESS(f'\nSuccessfully created {created_count} properties!'))
            self.stdout.write(f'Total properties in database: {Property.objects.count()}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
