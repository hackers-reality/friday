"""
Friday Cloud - Cloud provider integrations.
AWS, GCP, Azure, DigitalOcean with unified interface.
"""
from __future__ import annotations

import os
import sys
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import base64


# ─── AWS Integration ────────────────────────────#

class AWSClient:
    """AWS client (simplified)."""
    
    def __init__(self, access_key: str = None, secret_key: str = None, region: str = "us-east-1"):
        self.access_key = access_key or os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_key = secret_key or os.getenv("AWS_SECRET_ACCESS_KEY")
        self.region = region
        self.boto3_available = self._check_boto3()
        
    def _check_boto3(self) -> bool:
        try:
            import boto3
            self.boto3 = boto3
            return True
        except ImportError:
            return False
    
    def get_s3_client(self):
        """Get S3 client."""
        if not self.boto3_available:
            return None
        return self.boto3.client(
            "s3",
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
        )
    
    def list_s3_buckets(self) -> Dict[str, Any]:
        """List S3 buckets."""
        if not self.boto3_available:
            return {"success": False, "error": "boto3 not available. Install: pip install boto3"}
        
        try:
            s3 = self.get_s3_client()
            response = s3.list_buckets()
            buckets = [b["Name"] for b in response.get("Buckets", [])]
            return {"success": True, "buckets": buckets, "count": len(buckets)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_ec2_instances(self) -> Dict[str, Any]:
        """List EC2 instances."""
        if not self.boto3_available:
            return {"success": False, "error": "boto3 not available."}
        
        try:
            ec2 = self.boto3.client(
                "ec2",
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region,
            )
            response = ec2.describe_instances()
            instances = []
            for reservation in response.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    instances.append({
                        "id": instance["InstanceId"],
                        "state": instance["State"]["Name"],
                        "type": instance["InstanceType"],
                        "public_ip": instance.get("PublicIpAddress"),
                    })
            return {"success": True, "instances": instances, "count": len(instances)}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ─── GCP Integration ────────────────────────────#

class GCPClient:
    """GCP client (simplified)."""
    
    def __init__(self, project_id: str = None, credentials_path: str = None):
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID")
        self.credentials_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        self.google_cloud_available = self._check_google_cloud()
        
    def _check_google_cloud(self) -> bool:
        try:
            import google.cloud.storage
            return True
        except ImportError:
            return False
    
    def list_storage_buckets(self) -> Dict[str, Any]:
        """List GCS buckets."""
        if not self.google_cloud_available:
            return {"success": False, "error": "google-cloud-storage not available. Install: pip install google-cloud-storage"}
        
        try:
            from google.cloud import storage
            client = storage.Client()
            buckets = [b.name for b in client.list_buckets()]
            return {"success": True, "buckets": buckets, "count": len(buckets)}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ─── Azure Integration ────────────────────────────#

class AzureClient:
    """Azure client (simplified)."""
    
    def __init__(self, subscription_id: str = None, tenant_id: str = None):
        self.subscription_id = subscription_id or os.getenv("AZURE_SUBSCRIPTION_ID")
        self.tenant_id = tenant_id or os.getenv("AZURE_TENANT_ID")
        self.azure_available = self._check_azure()
        
    def _check_azure(self) -> bool:
        try:
            import azure.identity
            import azure.mgmt.resource
            return True
        except ImportError:
            return False
    
    def list_resource_groups(self) -> Dict[str, Any]:
        """List Azure resource groups."""
        if not self.azure_available:
            return {"success": False, "error": "azure-identity or azure-mgmt-resource not available."}
        
        try:
            from azure.identity import DefaultAzureCredential
            from azure.mgmt.resource import ResourceManagementClient
            
            credential = DefaultAzureCredential()
            client = ResourceManagementClient(credential, self.subscription_id)
            
            groups = [g.name for g in client.resource_groups.list()]
            return {"success": True, "resource_groups": groups, "count": len(groups)}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ─── DigitalOcean Integration ────────────────────────────#

class DigitalOceanClient:
    """DigitalOcean client (simplified)."""
    
    def __init__(self, token: str = None):
        self.token = token or os.getenv("DO_TOKEN")
        self.api_url = "https://api.digitalocean.com/v2"
        self.available = self.token is not None
        
    def _headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
    
    def list_droplets(self) -> Dict[str, Any]:
        """List DigitalOcean droplets."""
        if not self.available:
            return {"success": False, "error": "DigitalOcean token not set. Set DO_TOKEN environment variable."}
        
        try:
            import requests
            response = requests.get(f"{self.api_url}/droplets", headers=self._headers())
            if response.status_code == 200:
                data = response.json()
                droplets = [
                    {
                        "id": d["id"],
                        "name": d["name"],
                        "status": d["status"],
                        "ip": d.get("networks", {}).get("v4", [{}])[0].get("ip_address"),
                    }
                    for d in data.get("droplets", [])
                ]
                return {"success": True, "droplets": droplets, "count": len(droplets)}
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}
        except ImportError:
            return {"success": False, "error": "requests not available."}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ─── Cloud Tool for Friday ────────────────────────────#

def cloud_tool(
    action: str = "status",
    provider: str = "aws",
    params: Dict = None,
) -> str:
    """
    Friday tool for cloud operations.
    Actions: status, aws_s3_list, aws_ec2_list, gcp_buckets,
            azure_groups, do_droplets
    """
    params = params or {}
    
    if action == "status":
        lines = ["### CLOUD STATUS", ""]
        lines.append("**Available Providers**:")
        lines.append("  - AWS (S3, EC2)")
        lines.append("  - GCP (Storage)")
        lines.append("  - Azure (Resource Manager)")
        lines.append("  - DigitalOcean (Droplets)")
        return "\n".join(lines)
    
    if action == "aws_s3_list":
        aws = AWSClient(
            access_key=params.get("access_key"),
            secret_key=params.get("secret_key"),
            region=params.get("region", "us-east-1"),
        )
        result = aws.list_s3_buckets()
        if result["success"]:
            lines = ["### AWS S3 BUCKETS", ""]
            for bucket in result["buckets"]:
                lines.append(f"  - {bucket}")
            return "\n".join(lines)
        else:
            return f"[FAIL] AWS S3 error: {result.get('error', 'Unknown')}"
    
    if action == "aws_ec2_list":
        aws = AWSClient(
            access_key=params.get("access_key"),
            secret_key=params.get("secret_key"),
            region=params.get("region", "us-east-1"),
        )
        result = aws.list_ec2_instances()
        if result["success"]:
            lines = [f"### AWS EC2 INSTANCES ({result['count']})", ""]
            for instance in result["instances"]:
                lines.append(f"  - {instance['id']}: {instance['type']} ({instance['state']})")
            return "\n".join(lines)
        else:
            return f"[FAIL] AWS EC2 error: {result.get('error', 'Unknown')}"
    
    if action == "gcp_buckets":
        gcp = GCPClient(
            project_id=params.get("project_id"),
            credentials_path=params.get("credentials_path"),
        )
        result = gcp.list_storage_buckets()
        if result["success"]:
            lines = ["### GCP STORAGE BUCKETS", ""]
            for bucket in result["buckets"]:
                lines.append(f"  - {bucket}")
            return "\n".join(lines)
        else:
            return f"[FAIL] GCP error: {result.get('error', 'Unknown')}"
    
    if action == "azure_groups":
        azure = AzureClient(
            subscription_id=params.get("subscription_id"),
            tenant_id=params.get("tenant_id"),
        )
        result = azure.list_resource_groups()
        if result["success"]:
            lines = ["### AZURE RESOURCE GROUPS", ""]
            for group in result["resource_groups"]:
                lines.append(f"  - {group}")
            return "\n".join(lines)
        else:
            return f"[FAIL] Azure error: {result.get('error', 'Unknown')}"
    
    if action == "do_droplets":
        do = DigitalOceanClient(token=params.get("token"))
        result = do.list_droplets()
        if result["success"]:
            lines = [f"### DIGITALOCEAN DROPLETS ({result['count']})", ""]
            for droplet in result["droplets"]:
                lines.append(f"  - {droplet['name']}: {droplet['status']} (IP: {droplet.get('ip', 'N/A')})")
            return "\n".join(lines)
        else:
            return f"[FAIL] DigitalOcean error: {result.get('error', 'Unknown')}"
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Friday Cloud...\n")
    
    # Test status
    print("--- Cloud Status ---")
    print(cloud_tool("status"))
    
    # Test AWS (will fail without credentials)
    print("\n--- AWS S3 (no creds) ---")
    print(cloud_tool("aws_s3_list"))
