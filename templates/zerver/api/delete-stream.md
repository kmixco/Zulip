# Delete stream

Delete the stream for the given unique ID.

`DELETE {{ api_url }}/v1/streams/{stream_id}`

## Usage examples

{start_tabs}
{tab|python}

{generate_code_example(python)|/streams/{stream_id}:delete|example}

{tab|curl}

``` curl
curl -X DELETE {{ api_url }}/v1/streams/{stream_id} \
    -u BOT_EMAIL_ADDRESS:BOT_API_KEY
```

{end_tabs}

## Arguments

**Note**: The following arguments are all URL query parameters.

{generate_api_arguments_table|zulip.yaml|/streams/{stream_id}:delete}

## Response

#### Return values

* `stream_id`: The ID of a stream.

#### Example response

A typical successful JSON response may look like:

{generate_code_example|/streams/{stream_id}:delete|fixture(200)}

An example JSON response for when the supplied stream does not exist:

{generate_code_example|/streams/{stream_id}:delete|fixture(400)}
