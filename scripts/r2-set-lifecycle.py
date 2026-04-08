# One-time setup: python scripts/r2-set-lifecycle.py
"""Set lifecycle rule on R2 bucket for auto-expiration of archived logs."""

import argparse
import logging
import os
from pathlib import Path

import boto3
import yaml

_LOG = logging.getLogger(__name__)

HOME = Path.home()
PROJECT_ROOT = Path(__file__).parent.parent

CONFIG_FILE = PROJECT_ROOT / "configs" / "r2-config.yaml"
KEYS_FILE = HOME / ".config" / "bazzite-ai" / "keys.env"


def load_keys_env(keys_file: Path) -> dict[str, str]:
    """Parse key=value pairs from a keys env file."""
    result: dict[str, str] = {}
    try:
        for raw_line in keys_file.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip().strip('"').strip("'")
    except OSError:
        pass
    return result


def load_config(config_file: Path) -> dict:
    """Load R2 config from YAML."""
    try:
        with config_file.open() as f:
            return yaml.safe_load(f) or {}
    except OSError:
        return {}


def set_lifecycle_rule(
    bucket: str, endpoint: str, region: str, access_key: str, secret_key: str, expiration_days: int
) -> None:
    """Set lifecycle rule on R2 bucket to expire objects after N days."""
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )

    s3.put_bucket_lifecycle_configuration(
        Bucket=bucket,
        LifecycleConfiguration={
            "Rules": [
                {
                    "ID": "expire-logs-180d",
                    "Filter": {"Prefix": ""},
                    "Status": "Enabled",
                    "Expiration": {"Days": expiration_days},
                }
            ]
        },
    )

    _LOG.info("Lifecycle rule set: bucket=%s, expiration_days=%d", bucket, expiration_days)


def main() -> int:
    parser = argparse.ArgumentParser(description="Set R2 bucket lifecycle rule for log expiration.")
    parser.add_argument(
        "--days",
        type=int,
        default=180,
        metavar="N",
        help="Number of days before objects expire (default: 180)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    config = load_config(CONFIG_FILE)
    r2_cfg = config.get("r2", {})
    keys_cfg = config.get("keys", {})

    endpoint = r2_cfg.get("endpoint", "")
    if not endpoint:
        _LOG.error("R2 endpoint not configured in %s", CONFIG_FILE)
        return 1

    access_key_env = keys_cfg.get("access_key_env", "R2_ACCESS_KEY_ID")
    secret_key_env = keys_cfg.get("secret_key_env", "R2_SECRET_ACCESS_KEY")

    keys = load_keys_env(KEYS_FILE)
    access_key = keys.get(access_key_env) or os.environ.get(access_key_env, "")
    secret_key = keys.get(secret_key_env) or os.environ.get(secret_key_env, "")

    if not access_key:
        _LOG.error("R2 access key not set — cannot configure R2 lifecycle")
        return 1
    if not secret_key:
        _LOG.error("R2 secret key not set — cannot configure R2 lifecycle")
        return 1

    bucket = r2_cfg.get("bucket", "bazzite-logs")
    region = r2_cfg.get("region", "auto")

    try:
        set_lifecycle_rule(bucket, endpoint, region, access_key, secret_key, args.days)
        print(f"SUCCESS: Bucket '{bucket}' lifecycle rule set to expire after {args.days} days")
        return 0
    except Exception:
        _LOG.exception("Failed to set lifecycle rule")
        return 1


if __name__ == "__main__":
    exit(main())
