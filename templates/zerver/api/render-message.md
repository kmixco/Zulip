# Render message

Render a message to HTML.

`POST {{ api_url }}/v1/messages/render`

## Arguments

{generate_api_arguments_table|arguments.json|render-message.md}

## Usage examples
<div class="code-section" markdown="1">
<ul class="nav">
<li data-language="curl">curl</li>
<li data-language="python">Python</li>
</ul>
<div class="blocks">

<div data-language="curl" markdown="1">

```
curl {{ api_url }}/v1/messages/render \
    -u BOT_EMAIL_ADDRESS:BOT_API_KEY \
    -d "content=**foo**"

```
</div>

<div data-language="python" markdown="1">
```python
#!/usr/bin/env python

import zulip
import sys

# Keyword arguments 'email' and 'api_key' are not required if you are using ~/.zuliprc
client = zulip.Client(email="othello-bot@example.com",
                      api_key="a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5",
                      site="{{ api_url }}")

# Render a message
print(client.render_message({"content": "**foo**"}))
```
</div>

</div>

</div>

## Response

#### Return values

* `rendered`: The rendered HTML.

#### Example response

A typical successful JSON response may look like:

```
{
    'result':'success',
    'msg':'',
    'rendered':'<p><strong>foo</strong></p>'
}
```

A typical JSON response for when the required argument `content`
is not supplied:

```
{
    'code':'REQUEST_VARIABLE_MISSING',
    'result':'error',
    'msg':"Missing 'content' argument",
    'var_name':'content'
}
```

{!invalid-api-key-json-response.md!}
