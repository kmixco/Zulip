# Zulip Slack integration

Get Zulip notifications from Slack for messages on your team's public channels!
You can choose to map each **Slack channel** either to a **Zulip channel** or to
a **Zulip topic**.

See also the [Slack-compatible webhook](/integrations/doc/slack_incoming).

!!! warn ""

    Using [Slack's legacy Outgoing Webhook service][legacy_webhook_link] is no
    longer recommended. Follow these instructions to switch to the new Slack
    Event API.

{start_tabs}

1. To map Slack channels to Zulip topics, [create the
   channel](/help/create-a-channel) you'd like to use for Slack notifications.
   Otherwise, for each public Slack channel, [create a Zulip
   channel](/help/create-a-channel) with the same name.

1. {!create-an-incoming-webhook.md!}

1. {!generate-webhook-url-basic.md!}
   If mapping Slack channels to Zulip topics,
   make sure that the **Send all notifications to a single topic** option is
   disabled. Add `&channels_map_to_topics=1` to the URL you generated.
   Otherwise, add `&channels_map_to_topics=0` to the URL you generated; the
   Zulip channel you specified when generating the URL will be ignored.

1. Create a new [Slack app][slack_app_link], and open it. Navigate to
   the **OAuth & Permissions** menu, and scroll down to the **Scopes**
   section.

1. Make sure **Bot Token Scopes** includes `channels:read`,
   `channels:history`, `users:read`, `emoji:read`, `team:read`,
   `users:read`, and `users:read.email`.

    !!! tip ""

        See [Slack's Events API documentation][events_api_doc_link]
        for details about these scopes.

1. Scroll to the **OAuth Tokens for Your Workspace** section in the
   same menu, and click **Install to Workspace**.

1. The **Bot User OAuth Token** should be available now. Note it down as
   `BOT_OAUTH_TOKEN`, and add it to the end of the URL you generated
   above as: `&slack_app_token=BOT_OAUTH_TOKEN`.

1. Go to the **Event Subscriptions** menu, toggle **Enable Events**,
   and enter the URL with the bot user token in the **Request URL**
   field.

1. In the same menu, scroll down to the **Subscribe to bot events**
   section, and click on **Add Bot User Event**. Select the
   `message.channels` event.

{end_tabs}

{!congrats.md!}

![](/static/images/integrations/slack/001.png)

## Related documentation

- [Slack Events API documentation][events_api_doc_link]

- [Slack Apps][slack_app_link]

{!webhooks-url-specification.md!}

[events_api_doc_link]: https://api.slack.com/apis/events-api

[slack_app_link]: https://api.slack.com/apps

[legacy_webhook_link]: https://api.slack.com/legacy/custom-integrations/outgoing-webhooks
