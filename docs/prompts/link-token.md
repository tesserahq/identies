1. Generate link token

Purpose
* Generates a short-lived, single-use token (we will need a new model/schema/db migration probably)
* Bound to an external platform + external user id + data (optional)
* Expiration by default should be 10 mins but I want to be able to control that.


Endpoint POST /external-accounts/link-tokens

```json
{
  "platform": "telegram",
  "external_user_id": "123456789"
}

{
  "platform": "telegram",
  "external_user_id": "123456789",
  "data": {
    ....
  }
}
```


Response

{
  "token": "abc123",
  "expires_at": "2026-02-02T12:00:00Z",
}

2. Link external account

Purpose

* Links the current_user to the external account referenced by the token
* This is the only place where the association is created


POST /external-accounts/link

Request: 

```json
{
  "token": "abc123"
}
````

Behavior

* Validate token
* Resolve platform + external_user_id
* Create ExternalAccount
* Invalidate token


REsponse ExternalAccountResponse


3. Unlink external account

Purpose
* Allow users to revoke access

Endpoint: DELETE /external-accounts/{id}


4. List external accounts (use fastapi-pagination)

GET /external-accounts