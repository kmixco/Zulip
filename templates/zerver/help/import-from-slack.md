# Import from Slack

Starting with Zulip 1.8, Zulip supports importing data from Slack,
including users, channels, messages, attachments, avatars, custom
emoji, and emoji reactions.

This tool has been used to import Slack workspaces with 10,000 members
and millions of messages. If you're planning on doing an import much
larger than that, or run into performance issues when importing, email
us at support@zulipchat.com for help.

**Note:** You can only import a Slack workspace as a new Zulip
organization. In particular, you cannot use this tool to import from Slack
into an existing Zulip organization.

## Import from Slack

First, export your data from Slack.

### Export your Slack data

{start_tabs}

1. [Generate a Slack Legacy API
   token](https://api.slack.com/custom-integrations/legacy-tokens).
   It will be a long string starting with `xoxp-`.  It is required to
   fetch data that Slack doesn't include in their data exports, like
   email addresses.

2. [Export your Slack data](https://my.slack.com/services/export). You will
   receive a zip file `slack_data.zip`.

    !!! warn ""
        **Note:** Only Slack owners and admins can export data from Slack.
        See Slack's
        [guide to data exports](https://get.slack.help/hc/en-us/articles/201658943-Export-data-and-message-history)
        for more information.

    This step will also generate a different token starting with
    `xoxe-`; you don't need it.

{end_tabs}

### Import into zulipchat.com

Email support@zulipchat.com with `slack_data.zip`, the Slack API token
generated above, and your desired subdomain. Your imported organization will
be hosted at `<subdomain>.zulipchat.com`.

If you've already created a test organization at
`<subdomain>.zulipchat.com`, let us know, and we can rename the old
organization first.

### Import into a self-hosted Zulip server

First
[install a new Zulip server](https://zulip.readthedocs.io/en/stable/production/install.html),
skipping "Step 3: Create a Zulip organization, and log in" (you'll
create your Zulip organization via the data import tool instead).

Log in to a shell on your Zulip server as the `zulip` user. To import with
the most common configuration, run the following commands, replacing
`<token>` with the value generated above.

```
cd /home/zulip/deployments/current
./manage.py convert_slack_data slack_data.zip --token <token> --output converted_slack_data
./manage.py import '' converted_slack_data
```

This could take several minutes to run, depending on how much data you're
importing.

**Import options**

The commands above create an imported organization on the root domain
(`EXTERNAL_HOST`) of the Zulip installation. You can also import into a
custom subdomain, e.g. if you already have an existing organization on the
root domain. Replace the last line above with the following, after replacing
`<subdomain>` with the desired subdomain.

```
./manage.py import <subdomain> converted_slack_data
```

{!import-login.md!}

## Caveats

- Slack doesn't export private channels or direct messages unless you pay
  for Slack Plus or contact Slack support. See
  [Slack's documentation](https://get.slack.help/hc/en-us/articles/204897248-Guide-to-Slack-import-and-export-tools)
  for more details.

- (Slack Plus import) Message edit history is currently not imported.

- Slack doesn't export user settings or organization settings, so
  you'll need to configure these manually.

- Import of [user roles](/help/roles-and-permissions):
    - Slack's `Workspace Primary Owner`, `Workspace Owner`, and
      `Workspace Admin` users are mapped to Zulip's `Organization
      administrator` users.
    - Slack's `Member` users is mapped to Zulip `Member` users.
    - Slack's `Single Channel Guest` and `Multi Channel Guest` users
    are mapped to Zulip `Guest` users.
    - Slack's `Channel creators` have no special permissions in Zulip.

- The "joined #channel_name" messages are not imported.

[upgrade-zulip-from-git]: https://zulip.readthedocs.io/en/latest/production/upgrade-or-modify.html#upgrading-from-a-git-repository
