"""
Create MinIO buckets for NeuroLake
"""
from minio import Minio
from minio.error import S3Error

# Connect to MinIO
client = Minio(
    "localhost:9000",
    access_key="neurolake",
    secret_key="dev_password_change_in_prod",
    secure=False
)

# Create buckets
buckets = ["data", "temp"]

for bucket_name in buckets:
    try:
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            print(f"✓ Created bucket: {bucket_name}")
        else:
            print(f"✓ Bucket already exists: {bucket_name}")
    except S3Error as e:
        print(f"✗ Error creating bucket {bucket_name}: {e}")

# List all buckets
print("\nAll buckets:")
buckets = client.list_buckets()
for bucket in buckets:
    print(f"  - {bucket.name} (created: {bucket.creation_date})")
