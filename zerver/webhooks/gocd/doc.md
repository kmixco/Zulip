# Zulip GoCD integration

Get GoCD notifications in Zulip!

!!! warn ""

    **Note**: We currently only support version **v0.0.6** of Sentry's GoCD notification
    plugin.

{start_tabs}

1. {!create-channel.md!}

1. {!create-an-incoming-webhook.md!}

1. {!generate-webhook-url-basic.md!}

1. Download the jar file for Sentry's [**WebHook Notifier plugin**][gocd-webhook-link]
   and install it in your GoCD server.

1. In your GoCD server, go to **Admin>Server Configuration>Plugins**. Click
   on the gear icon beside the **WebHook Notifier plugin** you just installed,
   paste the generated URL, and click **Save**.

{end_tabs}

{!congrats.md!}

![](/static/images/integrations/gocd/001.png)

### Related Branches

- [GoCD plugins documentation][gocd-plugins-doc-link]

{!webhooks-url-specification.md!}

[gocd-webhook-link]: https://github.com/getsentry/gocd-webhook-notification-plugin/releases/tag/v0.0.6

[gocd-plugins-doc-link]: https://docs.gocd.org/current/extension_points/plugin_user_guide.html#installing-and-uninstalling-of-plugins
