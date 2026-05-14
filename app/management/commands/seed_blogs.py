from django.core.management.base import BaseCommand
from django.utils import timezone
from app.models import User, Blog, BlogCategory

class Command(BaseCommand):
    help = 'Seed blog categories and sample blog posts'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding blog data...')
        
        # Get or create admin user as author
        admin_user, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@psalms.com',
                'first_name': 'Admin',
                'last_name': 'User',
                'role': User.Role.SUPER_ADMIN,
                'is_staff': True,
                'is_superuser': True,
            }
        )
        
        # Create categories
        categories_data = [
            {'name': 'Property Management', 'description': 'Tips and insights on managing rental properties'},
            {'name': 'Real Estate', 'description': 'Latest trends in the real estate market'},
            {'name': 'Tenant Guide', 'description': 'Helpful information for tenants'},
            {'name': 'Landlord Tips', 'description': 'Best practices for landlords'},
            {'name': 'Market Insights', 'description': 'Analysis of property market trends'},
        ]
        
        categories = {}
        for cat_data in categories_data:
            category, created = BlogCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={'description': cat_data['description']}
            )
            categories[cat_data['name']] = category
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created category: {category.name}'))
        
        # Create sample blog posts
        blogs_data = [
            {
                'title': '10 Essential Tips for First-Time Landlords',
                'category': 'Landlord Tips',
                'excerpt': 'Starting your journey as a landlord? Here are the essential tips you need to know to succeed in property management and avoid common pitfalls.',
                'content': '''Becoming a landlord for the first time can be both exciting and overwhelming. Whether you've inherited a property or made an investment purchase, managing rental property requires knowledge, preparation, and dedication.

**1. Understand Local Landlord-Tenant Laws**
Before you rent out your property, familiarize yourself with local and state laws governing landlord-tenant relationships. These laws cover security deposits, eviction procedures, maintenance responsibilities, and tenant rights.

**2. Screen Tenants Thoroughly**
A good tenant can make your life easier, while a problematic one can be costly. Conduct thorough background checks, verify employment, check references, and review credit reports.

**3. Create a Detailed Lease Agreement**
Your lease agreement should be comprehensive and clearly outline all terms and conditions, including rent amount, payment due dates, late fees, maintenance responsibilities, and house rules.

**4. Set the Right Rent Price**
Research comparable properties in your area to set a competitive rent price. Consider factors like location, amenities, property size, and market demand.

**5. Budget for Maintenance and Repairs**
Set aside 1-2% of the property value annually for maintenance and unexpected repairs. Regular maintenance prevents costly emergency repairs.

**6. Keep Detailed Records**
Maintain organized records of all financial transactions, maintenance requests, communications with tenants, and property inspections.

**7. Consider Property Management Software**
Modern property management tools can help you organize rent collection, track maintenance, communicate with tenants, and manage finances efficiently.

**8. Build a Network of Reliable Contractors**
Develop relationships with trusted plumbers, electricians, handymen, and other professionals before you need them in an emergency.

**9. Conduct Regular Property Inspections**
Schedule periodic inspections to ensure your property is well-maintained and identify issues before they become major problems.

**10. Treat Your Rental as a Business**
Keep personal and business finances separate, track expenses for tax purposes, and approach landlording professionally.

Success as a landlord requires preparation, organization, and ongoing education. Start with these fundamentals and continue learning as you grow your rental property business.''',
                'tags': 'landlord, property management, rental property, first-time landlord, real estate investing',
                'read_time': 8,
            },
            {
                'title': 'Understanding Your Rights as a Tenant',
                'category': 'Tenant Guide',
                'excerpt': 'Every tenant has legal rights. Learn about your protections, responsibilities, and what to do if your landlord violates your rights.',
                'content': '''As a tenant, knowing your rights is crucial for maintaining a fair and legal relationship with your landlord. This guide covers the fundamental rights every tenant should be aware of.

**Right to Habitable Living Conditions**
Your landlord must provide a safe, clean, and habitable living space. This includes working plumbing, heating, electricity, and protection from environmental hazards.

**Right to Privacy**
Landlords must provide reasonable notice (typically 24-48 hours) before entering your rental unit, except in emergencies. You have the right to peaceful enjoyment of your home.

**Security Deposit Protection**
Most states have specific laws about security deposit amounts, how they must be stored, and the timeline for returning deposits after you move out.

**Protection from Discrimination**
The Fair Housing Act prohibits discrimination based on race, color, national origin, religion, sex, familial status, or disability. Some states offer additional protections.

**Right to Request Repairs**
When something breaks or needs repair, you have the right to request maintenance. Landlords must address serious issues promptly.

**Your Responsibilities**
While you have rights, you also have responsibilities including paying rent on time, keeping the property clean, reporting maintenance issues, and following lease terms.

**What to Do if Rights Are Violated**
Document everything, communicate in writing, know your local tenant resources, and consult with a tenant rights organization or attorney if necessary.

Understanding your rights empowers you to advocate for yourself and maintain a positive rental experience.''',
                'tags': 'tenant rights, renting, legal rights, fair housing, tenant protection',
                'read_time': 6,
            },
            {
                'title': 'Real Estate Market Trends for 2026',
                'category': 'Market Insights',
                'excerpt': 'Explore the latest trends shaping the real estate market in 2026, including pricing predictions, buyer behavior, and emerging hotspots.',
                'content': '''The real estate market in 2026 is experiencing significant shifts driven by economic factors, demographic changes, and evolving buyer preferences.

**Urban vs. Suburban Dynamics**
While cities are seeing renewed interest post-pandemic, suburban areas continue to attract families seeking space and affordability. Hybrid work models influence location decisions.

**Technology Integration**
Smart home features are no longer luxuries—they're expectations. Energy-efficient systems, integrated security, and automation are driving property values.

**Sustainability Focus**
Green buildings and energy-efficient properties command premium prices as buyers prioritize environmental impact and long-term cost savings.

**Interest Rate Impact**
Current interest rates significantly affect affordability and buyer purchasing power. Monitoring rate trends is crucial for both buyers and sellers.

**Inventory Challenges**
Many markets face housing shortages, driving competition and prices upward. New construction hasn't kept pace with demand in key areas.

**Investment Opportunities**
Multi-family properties and short-term rentals continue attracting investors, though regulations are tightening in some markets.

**Demographic Shifts**
Millennials entering prime homebuying years and Baby Boomers downsizing create unique market dynamics and opportunities.

**Regional Variations**
Market conditions vary dramatically by region. Research local trends and consult with area experts before making decisions.

Staying informed about market trends helps buyers, sellers, and investors make strategic decisions in this dynamic environment.''',
                'tags': 'real estate trends, market analysis, property investing, housing market, 2026 predictions',
                'read_time': 7,
            },
            {
                'title': 'How to Prepare Your Property for Rent',
                'category': 'Property Management',
                'excerpt': 'Get your property rent-ready with this comprehensive checklist covering repairs, upgrades, and legal requirements.',
                'content': '''Preparing a property for rent requires attention to detail, strategic improvements, and legal compliance. Follow this guide to attract quality tenants and maximize your rental income.

**Safety and Legal Requirements**
Install smoke detectors and carbon monoxide detectors, ensure all electrical and plumbing systems meet code, address any lead paint or asbestos concerns, and obtain necessary permits and certificates.

**Essential Repairs**
Fix any structural issues, repair or replace damaged flooring, address plumbing leaks, ensure all appliances work properly, and fix any cosmetic damage like holes in walls.

**Cosmetic Improvements**
Fresh paint in neutral colors makes spaces feel clean and new. Clean or replace carpets, update outdated light fixtures, and enhance curb appeal with landscaping.

**Deep Cleaning**
Professional cleaning shows pride of ownership and helps tenants envision themselves in the space. Pay special attention to kitchens, bathrooms, and windows.

**Documentation**
Take detailed photos of the property condition before tenants move in. This protects both you and your tenants during the move-out process.

**Set Competitive Rent**
Research comparable properties in your area and consider your property's condition, location, and amenities when setting rent prices.

**Marketing Your Property**
Create compelling listings with high-quality photos, detailed descriptions, and highlight unique features that set your property apart.

**Tenant Screening Process**
Establish a consistent screening process that includes application review, credit checks, employment verification, and reference checks.

Proper preparation attracts responsible tenants, reduces vacancy periods, and sets the foundation for a positive landlord-tenant relationship.''',
                'tags': 'property preparation, rental property, landlord guide, property management, tenant attraction',
                'read_time': 9,
            },
            {
                'title': 'The Benefits of Professional Property Management',
                'category': 'Property Management',
                'excerpt': 'Discover how professional property management can save you time, reduce stress, and potentially increase your rental income.',
                'content': '''Professional property management offers numerous advantages for property owners, especially those with multiple properties or limited time.

**Time Savings**
Property managers handle day-to-day operations including tenant communications, maintenance coordination, rent collection, and emergency calls—freeing up your valuable time.

**Tenant Screening Expertise**
Professional managers have refined screening processes and experience identifying reliable tenants, reducing your risk of problematic tenancies.

**Legal Compliance**
Property management companies stay current with changing landlord-tenant laws, fair housing regulations, and local ordinances, protecting you from costly legal mistakes.

**Maintenance Network**
Established relationships with reliable contractors mean faster repairs at competitive prices. Emergency situations are handled promptly and professionally.

**Higher Occupancy Rates**
Effective marketing, competitive pricing strategies, and professional service help minimize vacancy periods and attract quality long-term tenants.

**Financial Management**
Detailed accounting, timely rent collection, expense tracking, and financial reporting give you clear insights into your property's performance.

**Reduced Stress**
Delegate tenant conflicts, late-night emergencies, and day-to-day issues to professionals while you focus on growing your investment portfolio.

**Market Knowledge**
Local market expertise helps you make informed decisions about rental rates, property improvements, and investment opportunities.

**Cost Considerations**
Management fees typically range from 8-12% of monthly rent. Calculate whether the benefits outweigh the costs for your situation.

**Choosing the Right Manager**
Research companies thoroughly, check references, review contracts carefully, and ensure they align with your investment goals.

For many property owners, professional management is a worthwhile investment that enhances returns while reducing personal burden.''',
                'tags': 'property management, professional services, rental management, landlord services, property investment',
                'read_time': 7,
            },
            {
                'title': 'Smart Home Features Tenants Want in 2026',
                'category': 'Real Estate',
                'excerpt': 'Modern tenants expect smart home technology. Learn which features attract quality renters and command higher rent.',
                'content': '''Smart home technology has evolved from luxury to expectation. Properties with these features attract tech-savvy tenants and justify premium rent prices.

**Smart Locks and Entry Systems**
Keyless entry provides convenience and security. Tenants appreciate the ability to grant access to guests and service providers remotely.

**Smart Thermostats**
Energy-efficient climate control saves money and appeals to environmentally conscious renters. Remote temperature adjustment is a valued convenience.

**Security Systems**
Integrated cameras, doorbell cameras, and motion sensors provide peace of mind. Cloud-based monitoring allows tenants to check their home from anywhere.

**Smart Lighting**
Programmable lighting systems offer convenience, energy savings, and customization. Voice control integration with systems like Alexa or Google Home adds appeal.

**Energy Monitoring**
Devices that track energy usage help tenants manage utility costs and appeal to sustainability-minded renters.

**Smart Appliances**
WiFi-enabled appliances offer convenience and efficiency. Features like smartphone control for ovens, refrigerators, and laundry machines are increasingly popular.

**Voice Assistants**
Integration with virtual assistants creates seamless smart home experiences and appeals to tech-forward tenants.

**Water Leak Detectors**
Prevent costly damage with smart sensors that alert both tenants and landlords to potential plumbing issues.

**Implementation Considerations**
Choose reliable, widely-compatible systems. Consider privacy implications and clearly communicate data policies to tenants.

**ROI Analysis**
While smart features require upfront investment, they can justify higher rent, reduce maintenance costs, and attract quality long-term tenants.

Strategic smart home upgrades differentiate your property in competitive rental markets and appeal to the growing demographic of tech-savvy renters.''',
                'tags': 'smart home, property technology, modern amenities, rental features, tenant preferences',
                'read_time': 8,
            },
        ]
        
        for blog_data in blogs_data:
            category = categories.get(blog_data['category'])
            blog, created = Blog.objects.get_or_create(
                title=blog_data['title'],
                defaults={
                    'author': admin_user,
                    'category': category,
                    'excerpt': blog_data['excerpt'],
                    'content': blog_data['content'],
                    'tags': blog_data['tags'],
                    'read_time': blog_data['read_time'],
                    'status': Blog.Status.PUBLISHED,
                    'published_at': timezone.now(),
                    'is_featured': False,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created blog: {blog.title}'))
        
        # Mark first two blogs as featured
        Blog.objects.filter(title__in=[
            '10 Essential Tips for First-Time Landlords',
            'Real Estate Market Trends for 2026'
        ]).update(is_featured=True)
        
        self.stdout.write(self.style.SUCCESS('Blog seeding completed successfully!'))
