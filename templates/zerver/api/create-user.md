# Create a user

Create a new user in a realm.

**Note**: The requesting user must be an administrator.

`POST {{ api_url }}/v1/users`

## Arguments

{generate_api_arguments_table|arguments.json|create-user.md}

## Usage examples
<div class="code-section" markdown="1">
<ul class="nav">
<li data-language="curl">curl</li>
<li data-language="python">Python</li>
</ul>
<div class="blocks">

<div data-language="curl" markdown="1">

```
curl {{ api_url }}/v1/users \
    -u BOT_EMAIL_ADDRESS:BOT_API_KEY \
    -d "email=newbie@zulip.com" \
    -d "full_name=New User" \
    -d "short_name=newbie" \
    -d "password=temp"

```

</div>

<div data-language="python" markdown="1">

```python
#!/usr/bin/env python

import zulip

# You need a zuliprc-admin with administrator credentials
client = zulip.Client(config_file="~/zuliprc-admin")

# Create a user
print(client.create_user({
    'email': 'newbie@zulip.com',
    'password': 'temp',
    'full_name': 'New User',
    'short_name': 'newbie'
}))
```

</div>

</div>

</div>

## Response

#### Example response

A typical successful JSON response may look like:

```
{
    'result':'success',
    'msg':''
}
```

A typical JSON response for when another user with the same
email address already exists in the realm:

```
{
    'msg':"Email 'newbie@zulip.com' already in use",
    'result':'error'
}
```

{!invalid-api-key-json-response.md!}
