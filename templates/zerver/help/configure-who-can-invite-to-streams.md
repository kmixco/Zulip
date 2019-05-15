# Restrict stream invitation

{!admin-only.md!}

By default, anyone other than guests can invite others to streams. However, you can restrict stream
invitation to:

* **Organization administrators and members**
* **Organization administrators**
* **Organization administrators, and members with accounts at least `N` days old**, for some `N`.

For corporations and other entities with controlled access, we highly
recommend keeping stream invitation open.

For entities with lots of streams with confidential contents, it may be desirable
to limit invitations.

### Manage who can create streams

{start_tabs}

{settings_tab|organization-permissions}

2. Under **Other permissions**, configure **Who can invite other users to streams**.

{!save-changes.md!}

{end_tabs}
