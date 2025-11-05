"""
File: s3_manager.py
Purpose: S3 storage management with tenant isolation
Main functionality: Upload, download, and manage S3 files with company_id segregation
Dependencies: boto3, Flask
"""

import boto3
from botocore.exceptions import ClientError
from typing import Optional, BinaryIO
import os
from datetime import timedelta


class S3Manager:
    """
    S3 storage manager with strict tenant isolation
    
    All S3 paths follow the pattern:
    s3://kantan-ai-manual-generator/{company_id}/{resource_type}/{resource_id}/
    """
    
    def __init__(self):
        self.bucket_name = os.getenv('AWS_S3_BUCKET_NAME', 'kantan-ai-manual-generator')
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'ap-northeast-1')
        )
    
    def get_material_path(self, company_id: int, material_id: int, filename: str) -> str:
        """Generate S3 key for reference material"""
        return f"{company_id}/materials/{material_id}/{filename}"
    
    def get_pdf_path(self, company_id: int, manual_id: int, language_code: str, filename: str) -> str:
        """Generate S3 key for generated PDF"""
        return f"{company_id}/pdfs/{manual_id}/{language_code}/{filename}"
    
    def get_temp_path(self, company_id: int, job_id: int, filename: str) -> str:
        """Generate S3 key for temporary processing files"""
        return f"{company_id}/temp/{job_id}/{filename}"
    
    def validate_company_access(self, company_id: int, s3_key: str) -> bool:
        """
        Verify that s3_key belongs to the specified company_id
        Prevents cross-tenant data access
        """
        expected_prefix = f"{company_id}/"
        return s3_key.startswith(expected_prefix)
    
    def upload_file(self, file_obj: BinaryIO, s3_key: str, 
                    content_type: str = 'application/octet-stream') -> str:
        """
        Upload file object to S3
        
        Args:
            file_obj: File-like object to upload
            s3_key: S3 object key (path within bucket)
            content_type: MIME type of the file
        
        Returns:
            S3 URI (s3://bucket/key)
        """
        try:
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'ServerSideEncryption': 'AES256'
                }
            )
            return f"s3://{self.bucket_name}/{s3_key}"
        
        except ClientError as e:
            raise Exception(f"S3 upload failed: {str(e)}")
    
    def upload_from_path(self, local_path: str, s3_key: str,
                         content_type: str = 'application/octet-stream') -> str:
        """
        Upload file from local path to S3
        
        Args:
            local_path: Local file path
            s3_key: S3 object key
            content_type: MIME type of the file
        
        Returns:
            S3 URI (s3://bucket/key)
        """
        try:
            with open(local_path, 'rb') as file_obj:
                return self.upload_file(file_obj, s3_key, content_type)
        
        except FileNotFoundError:
            raise Exception(f"Local file not found: {local_path}")
    
    def download_file(self, s3_key: str, local_path: str) -> None:
        """
        Download file from S3 to local path
        
        Args:
            s3_key: S3 object key
            local_path: Destination local path
        """
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            self.s3_client.download_file(
                self.bucket_name,
                s3_key,
                local_path
            )
        
        except ClientError as e:
            raise Exception(f"S3 download failed: {str(e)}")
    
    def generate_presigned_url(self, s3_key: str, expiration: int = 3600) -> str:
        """
        Generate presigned URL for temporary access
        
        Args:
            s3_key: S3 object key
            expiration: URL expiration time in seconds (default: 1 hour)
        
        Returns:
            Presigned URL
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            return url
        
        except ClientError as e:
            raise Exception(f"Failed to generate presigned URL: {str(e)}")
    
    def delete_file(self, s3_key: str) -> None:
        """
        Delete file from S3
        
        Args:
            s3_key: S3 object key
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
        
        except ClientError as e:
            raise Exception(f"S3 delete failed: {str(e)}")
    
    def delete_folder(self, company_id: int, folder_prefix: str) -> None:
        """
        Delete all files in a folder (company_id is enforced)
        
        Args:
            company_id: Company ID for tenant isolation
            folder_prefix: Folder prefix within company namespace
        """
        s3_prefix = f"{company_id}/{folder_prefix}"
        
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=s3_prefix
            )
            
            for page in pages:
                if 'Contents' in page:
                    objects = [{'Key': obj['Key']} for obj in page['Contents']]
                    if objects:
                        self.s3_client.delete_objects(
                            Bucket=self.bucket_name,
                            Delete={'Objects': objects}
                        )
        
        except ClientError as e:
            raise Exception(f"S3 folder delete failed: {str(e)}")
    
    def file_exists(self, s3_key: str) -> bool:
        """
        Check if file exists in S3
        
        Args:
            s3_key: S3 object key
        
        Returns:
            True if file exists, False otherwise
        """
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True
        
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise Exception(f"S3 check failed: {str(e)}")
    
    def get_file_size(self, s3_key: str) -> int:
        """
        Get file size in bytes
        
        Args:
            s3_key: S3 object key
        
        Returns:
            File size in bytes
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return response['ContentLength']
        
        except ClientError as e:
            raise Exception(f"Failed to get file size: {str(e)}")


s3_manager = S3Manager()
