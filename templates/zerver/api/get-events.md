{generate_api_title(/events:get)}

{generate_api_description(/events:get)}

## Usage examples

{start_tabs}
{tab|python}

```
#!/usr/bin/env python

import sys
import zulip

# Pass the path to your zuliprc file here.
client = zulip.Client(config_file="~/zuliprc")

# If you already have a queue registered and thus, have a queue_id
# on hand, you may use client.get_events() and pass in the above
# parameters, like so:
print(client.get_events(
    queue_id="1515010080:4",
    last_event_id=-1
))
```

`call_on_each_message` and `call_on_each_event` will automatically register
a queue for you.

{generate_code_example(javascript)|/events:get|example}

{tab|curl}

{generate_code_example(curl)|/events:get|example}

{end_tabs}

## Parameters

{generate_api_arguments_table|zulip.yaml|/events:get}

## Response

{generate_return_values_table|zulip.yaml|/events:get}

{generate_response_description(/events:get)}

#### Example response

{generate_code_example|/events:get|fixture(200)}

{generate_code_example|/events:get|fixture(400)}
