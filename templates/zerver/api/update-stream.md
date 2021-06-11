{generate_api_title(/streams/{stream_id}:patch)}

{generate_api_description(/streams/{stream_id}:patch)}

## Usage examples

{start_tabs}
{tab|python}

{generate_code_example(python)|/streams/{stream_id}:patch|example}

{generate_code_example(javascript)|/streams/{stream_id}:patch|example}

{tab|curl}

{generate_code_example(curl, include=["new_name", "description", "is_private"])|/streams/{stream_id}:patch|example}

{end_tabs}

## Parameters

{generate_api_arguments_table|zulip.yaml|/streams/{stream_id}:patch}

## Response

#### Example response

{generate_code_example|/streams/{stream_id}:patch|fixture(200)}

{generate_code_example|/streams/{stream_id}:patch|fixture(400)}
