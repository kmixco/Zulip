{generate_api_title(/mark_all_as_read:post)}

{generate_api_description(/mark_all_as_read:post)}

## Usage examples

{start_tabs}
{tab|python}

{generate_code_example(python)|/mark_all_as_read:post|example}

{generate_code_example(javascript)|/mark_all_as_read:post|example}

{tab|curl}

{generate_code_example(curl)|/mark_all_as_read:post|example}

{end_tabs}

## Parameters

{generate_api_arguments_table|zulip.yaml|/mark_all_as_read:post}

## Response

#### Example response

{generate_code_example|/mark_all_as_read:post|fixture(200)}

{generate_code_example|/mark_all_as_read:post|fixture(400)}

{generate_api_title(/mark_stream_as_read:post)}

{generate_api_description(/mark_stream_as_read:post)}

`POST {{ api_url }}/v1/mark_stream_as_read`

## Usage examples

{start_tabs}
{tab|python}

{generate_code_example(python)|/mark_stream_as_read:post|example}

{generate_code_example(javascript)|/mark_all_as_read:post|example}

{tab|curl}

{generate_code_example(curl)|/mark_stream_as_read:post|example}

{end_tabs}

## Parameters

{generate_api_arguments_table|zulip.yaml|/mark_stream_as_read:post}

## Response

#### Example response

{generate_code_example|/mark_stream_as_read:post|fixture(200)}

{generate_code_example|/mark_stream_as_read:post|fixture(400)}

# Mark messages in a topic as read
{generate_api_title(/mark_topic_as_read:post)}

{generate_api_description(/mark_all_as_read:post)}

`POST {{ api_url }}/v1/mark_topic_as_read`

## Usage examples

{start_tabs}
{tab|python}

{generate_code_example(python)|/mark_topic_as_read:post|example}

{generate_code_example(javascript)|/mark_all_as_read:post|example}

{tab|curl}

{generate_code_example(curl)|/mark_topic_as_read:post|example}

{end_tabs}

## Parameters

{generate_api_arguments_table|zulip.yaml|/mark_topic_as_read:post}

## Response

#### Example response

{generate_code_example|/mark_topic_as_read:post|fixture(200)}

{generate_code_example|/mark_topic_as_read:post|fixture(400)}
