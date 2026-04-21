import aioboto3
import os
import logging
from typing import Optional
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        self.endpoint_url = os.getenv("S3_ENDPOINT_URL")
        self.access_key = os.getenv("S3_ACCESS_KEY")
        self.secret_key = os.getenv("S3_SECRET_KEY")
        self.bucket = os.getenv("S3_BUCKET_NAME")
        self.region = os.getenv("S3_REGION", "auto")
        
        self.session = aioboto3.Session()

    async def upload_file(self, content: bytes, file_name: str, content_type: str) -> Optional[str]:
        """
        Uploads a file to the S3-compatible storage and returns the public URL.
        """
        if not all([self.endpoint_url, self.access_key, self.secret_key, self.bucket]):
            logger.warning("S3 credentials not fully configured. Falling back to null storage.")
            return None

        async with self.session.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region
        ) as s3:
            try:
                await s3.put_object(
                    Bucket=self.bucket,
                    Key=file_name,
                    Body=content,
                    ContentType=content_type
                )
                
                # Construct public URL (this depends on the provider, 
                # but for R2/S3 it's usually endpoint/bucket/key or custom domain)
                # We'll assume a standard structure or custom domain if provided
                base_url = os.getenv("S3_PUBLIC_URL", f"{self.endpoint_url}/{self.bucket}")
                return f"{base_url}/{file_name}"
                
            except ClientError as e:
                logger.error(f"Error uploading file {file_name} to S3: {str(e)}")
                return None

storage_service = StorageService()
