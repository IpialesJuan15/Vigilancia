"""Private object storage; callers supply generated keys, never uploaded filenames."""

from pathlib import Path

from app.config import get_settings


class ObjectStore:
    def __init__(self):
        self.settings = get_settings()

    def _s3(self):
        import boto3

        return boto3.client(
            "s3",
            endpoint_url=self.settings.s3_endpoint,
            aws_access_key_id=self.settings.s3_access_key,
            aws_secret_access_key=self.settings.s3_secret_key,
            region_name="us-east-1",
        )

    def put(self, key: str, data: bytes):
        if self.settings.storage_backend == "local":
            path = Path(self.settings.storage_dir) / key
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            return
        from botocore.exceptions import ClientError

        s3 = self._s3()
        try:
            s3.head_bucket(Bucket=self.settings.s3_bucket)
        except ClientError as exc:
            if str(exc.response["Error"]["Code"]) not in {"404", "NoSuchBucket"}:
                raise
            try:
                s3.create_bucket(Bucket=self.settings.s3_bucket)
            except ClientError as create:
                if create.response["Error"]["Code"] not in {
                    "BucketAlreadyOwnedByYou",
                    "BucketAlreadyExists",
                }:
                    raise
        s3.put_object(Bucket=self.settings.s3_bucket, Key=key, Body=data)

    def get(self, key: str) -> bytes:
        if self.settings.storage_backend == "local":
            return (Path(self.settings.storage_dir) / key).read_bytes()
        return self._s3().get_object(Bucket=self.settings.s3_bucket, Key=key)["Body"].read()
