PARTITION_LEAD_REGIONS: dict[str, str] = {
    "aws": "us-east-1",
    "aws-cn": "cn-north-1",
    "aws-us-gov": "us-gov-west-1",
}
BACKUP_BUCKET_NAME_PREFIX = "jupyter-deploy-projects"
BACKUP_DDB_TABLE_NAME = "jupyter-deploy-projects"
BACKUP_TAG_SOURCE_KEY = "Source"
BACKUP_TAG_SOURCE_VALUE = "jupyter-deploy-cli"
BACKUP_TAG_VERSION_KEY = "Version"
