---
language: python
domain: security
type: pattern
title: Input validation with marshmallow
tags: input-validation, schema-validation, marshmallow, security
---

# Input Validation with Marshmallow

Never trust user input. This pattern shows how to validate structured data using Marshmallow, a powerful Python serialization and validation library.

## Why Marshmallow?

- Declarative schema definition
- Built-in validators for common patterns
- Integrates with Flask, FastAPI, and other frameworks
- Custom validators for complex logic

## Basic Schema

```python
from marshmallow import Schema, fields, validate, validates, ValidationError

class UserRegistrationSchema(Schema):
    username = fields.String(
        required=True,
        validate=validate.Length(min=3, max=50)
    )
    email = fields.Email(required=True)
    password = fields.String(
        load_only=True,
        validate=validate.Length(min=8)
    )
    age = fields.Integer(
        validate=validate.Range(min=13, max=120)
    )
```

## Custom Validators

```python
class SecurePasswordSchema(Schema):
    password = fields.String(required=True)
    
    @validates("password")
    def validate_password_strength(self, value):
        if not re.search(r"[A-Z]", value):
            raise ValidationError("Password must contain uppercase letter")
        if not re.search(r"[a-z]", value):
            raise ValidationError("Password must contain lowercase letter")
        if not re.search(r"[0-9]", value):
            raise ValidationError("Password must contain digit")
        if not re.search(r"[!@#$%^&*]", value):
            raise ValidationError("Password must contain special character")
```

## Usage in API Endpoints

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/register", methods=["POST"])
def register():
    schema = UserRegistrationSchema()
    try:
        data = schema.load(request.get_json())
        # Data is validated - proceed with business logic
        return jsonify({"status": "created"}), 201
    except ValidationError as err:
        return jsonify({"errors": err.messages}), 400
```

## Integration with Rate Limiting

Combine validation with rate limiting for comprehensive input handling:

```python
from ai.rate_limiter import RateLimiter

rate_limiter = RateLimiter()

@app.before_request
def check_rate_limit():
    client_id = request.headers.get("X-Client-ID", "anonymous")
    if not rate_limiter.can_call(f"api:{client_id}"):
        return jsonify({"error": "Rate limit exceeded"}), 429
```

## Best Practices

1. **Fail closed**: Default to rejecting invalid input
2. **Log validation failures**: Detect attack patterns
3. **Use strong validators**: Length, regex, range checks
4. **Sanitize on output**: Escape HTML, etc. after validation
5. **Version schemas**: Handle API evolution gracefully

This pattern ensures your APIs only accept well-formed, expected data.