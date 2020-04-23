# Create a user

{!api-admin-only.md!}

Create a new user account via the API.

`POST {{ api_url }}/v1/users`

## Usage examples

{start_tabs}
{tab|python}

{generate_code_example(python)|/users:post|example(admin_config=True)}

{tab|js}

More examples and documentation can be found [here](https://github.com/zulip/zulip-js).
{generate_code_example(JavaScript)|/users:post|example(admin_config=True)}

{tab|curl}

{generate_code_example(curl)|/users:post|example}

{end_tabs}

## Arguments

{generate_api_arguments_table|zulip.yaml|/users:post}

## Response

#### Example response

A typical successful JSON response may look like:

{generate_code_example|/users:post|fixture(200)}

A typical JSON response for when another user with the same
email address already exists in the realm:

{generate_code_example|/users:post|fixture(400)}
