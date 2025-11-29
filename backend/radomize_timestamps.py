import json
from datetime import datetime, timedelta
import random

filepath = r'c:\Users\bohdan\Desktop\strangers\Strangers-2025\backend\data.json'

# Load data
with open(filepath, 'r') as f:
    data = json.load(f)

# Get current time and 48 hours ago
now = datetime.utcnow()
time_48h_ago = now - timedelta(hours=48)

def generate_random_timestamp():
    """Generate a random timestamp within the last 48 hours"""
    random_seconds = random.uniform(0, 48 * 3600)
    random_timestamp = time_48h_ago + timedelta(seconds=random_seconds)
    return random_timestamp.isoformat() + 'Z'

# Update all timestamps in history
for item in data.get('history', []):
    item['timestamp'] = generate_random_timestamp()

# Update all timestamps in devices_data
for device in data.get('devices_data', []):
    for session in device.get('sessions', []):
        session['timestamp'] = generate_random_timestamp()

# Save the migrated data
with open(filepath, 'w') as f:
    json.dump(data, f, indent=2)

print('Migration complete! Assigned random timestamps (last 48 hours) to all timestamps in data.json')
