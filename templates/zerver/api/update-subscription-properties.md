# Update subscription properties

Make bulk modifications of the subscription properties on one or more streams
the user is subscribed to.

`POST {{ api_url }}/v1/users/me/subscriptions/properties`

## Usage examples

<div class="code-section" markdown="1">
<ul class="nav">
<li data-language="python">Python</li>
<li data-language="curl">curl</li>
</ul>
<div class="blocks">

<div data-language="curl" markdown="1">

```
curl -X POST {{ api_url }}/v1/users/me/subscriptions/properties \
    -u BOT_EMAIL_ADDRESS:BOT_API_KEY \
    -d 'subscription_data=[{"stream_id": 1, \
                            "property": "pin_to_top", \
                            "value": true}, \
                           {"stream_id": 3, \
                            "property": "color", \
                            "value": 'f00'}]'
```

</div>

<div data-language="python" markdown="1">

{generate_code_example(python)|/users/me/subscriptions/properties:post|example}

</div>

</div>

</div>

## Arguments

{generate_api_arguments_table|zulip.yaml|/users/me/subscriptions/properties:post}

The possible values for each `property` and `value` pairs are:

* `color` (string): the hex value of the stream's display color.
* `in_home_view` (boolean): whether the stream should be visible in the home
    view (`true`) or muted and thus hidden from the home view (`false`).
* `pin_to_top` (boolean): whether the stream should be fixed at the top of the
    stream list or not.
* `desktop_notifications` (boolean): whether to show desktop notifications
    for that stream or not.
* `audible_notifications` (boolean): whether to play a sound when a message
    from that stream is received or not.
* `push_notifications` (boolean): whether to show notifications in the mobile
    app for that stream or not.

## Response

#### Return values

* `subscription_data`: The same `subscription_data` object sent by the client
    for the request.

#### Example response

A typical successful JSON response may look like:

{generate_code_example|/users/me/subscriptions/properties:post|fixture(200)}
