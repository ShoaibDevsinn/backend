import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'house_price_prediction_system.settings')
django.setup()

from listings.models import Location

# List of Lahore locations
lahore_locations = [
    'DHA (Defence Housing Authority)',
    'Gulberg',
    'Johar Town',
    'Model Town',
    'Bahria Town',
    'Wapda Town',
    'Valencia Town',
    'Canal Road',
    'Faisal Town',
    'Askari XI',
    'Park View',
    'Sukh Chayn Gardens',
    'Lake City',
    'Iqbal Town',
    'Garden Town',
    'Allama Iqbal Town',
    'Muslim Town',
    'Punjab Cooperative Housing Society',
    'State Life Society',
    'Al-Rehman Garden'
]

print("=" * 50)
print("Inserting Lahore Locations")
print("=" * 50)

inserted = 0
skipped = 0

for location in lahore_locations:
    obj, created = Location.objects.get_or_create(
        location_name=location,
        defaults={'city': 'Lahore'}
    )
    if created:
        inserted += 1
        print(f"✅ Inserted: {location}")
    else:
        skipped += 1
        print(f"⚠️ Already exists: {location}")

print("=" * 50)
print(f"✅ New locations inserted: {inserted}")
print(f"⚠️ Already existed: {skipped}")
print(f"📊 Total locations in database: {Location.objects.count()}")
print("=" * 50)