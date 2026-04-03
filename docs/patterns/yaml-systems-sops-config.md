---
language: yaml
domain: systems
type: pattern
title: SOPS configuration for secrets
tags: sops, age, secrets-encryption, configuration, devops
---

# SOPS Configuration for Secrets

Use SOPS (Secrets OPerationS) to encrypt sensitive configuration values.

## Basic SOPS Setup

```yaml
# .sops.yaml - define encryption rules
creation_rules:
  - path_regex: ^secrets/.*
    encrypted_regex: "^(api_key|password|secret)$"
    age: >-
      age1abc123def456...
```

## Age Key Setup

```bash
# Generate age key (add to ~/.config/sops/age/keys.txt)
age-keygen > age-key.txt

# Or use existing SSH key
export SOPS_AGE_KEY_FILE=~/.ssh/id_ed25519
```

## Encrypted Configuration

```yaml
# config.yaml - with SOPS encryption
# Encrypted with SOPS - DO NOT EDIT DIRECTLY

some_value: "plaintext is fine"
api_key: ENC[AES256_GCM,adfg123...,realdata]
database_password: ENC[AES256_GCM,hij456...,realdata]
```

## Encrypting Secrets

```bash
# Encrypt a single value
sops set config.yaml "api_key" "new-secret-value"

# Encrypt entire file
sops encrypt config.yaml > config.encrypted.yaml

# Decrypt for viewing
sops decrypt config.encrypted.yaml
```

## Using in Application

```python
import subprocess
import json

def get_secrets() -> dict:
    """Load and decrypt secrets via sops."""
    result = subprocess.run(
        ["sops", "-d", "--output-type", "json", "secrets.yaml"],
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)
```

## YAML Structure with Multiple Environments

```yaml
# secrets.yaml.sops - encrypted values

development:
  api_key: ENC[AES256_GCM,...,data]
  db_pass: ENC[AES256_GCM,...,data]

production:
  api_key: ENC[AES256_GCM,...,data]
  db_pass: ENC[AES256_GCM,...,data]

staging:
  api_key: ENC[AES256_GCM,...,data]
  db_pass: ENC[AES256_GCM,...,data]
```

## Version Control

```bash
# .gitignore - exclude decrypted files
*.yaml
!*.yaml.sops

# Track encrypted versions
git add secrets.yaml.sops
```

## CI/CD Integration

```yaml
# .gitlab-ci.yml example
stages:
  - deploy

deploy:
  stage: deploy
  image: mozilla/sops:latest
  before_script:
    - echo "$AGE_KEY" > age.key
    - export SOPS_AGE_KEY_FILE=age.key
  script:
    - sops -d secrets.yaml | some-tool --
```

## Key Rotation

```bash
# Add new key to .sops.yaml
creation_rules:
  - path_regex: ^secrets/.*
    age: >-
      age1newkey...
      age1oldkey...  # Keep old for decryption

# Re-encrypt all files
find . -name "*.yaml.sops" -exec sops update {} \;
```

This pattern manages secrets securely across environments.