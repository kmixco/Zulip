# PostgreSQL database details

Starting with Zulip 3.0, Zulip supports a range of PostgreSQL
versions:

```{include} postgresql-support-table.md

```

We recommend that installations [upgrade to the latest
PostgreSQL][upgrade-postgresql] supported by their version of Zulip.

[upgrade-postgresql]: upgrade.md#upgrading-postgresql

## Separate PostgreSQL database

It is possible to run Zulip against a PostgreSQL database which is not on the
primary application server. There are two possible flavors of this -- using a
managed PostgreSQL instance from a cloud provider, or separating the PostgreSQL
server onto a separate (but still Zulip-managed) server for scaling purposes.

### Cloud-provider-managed PostgreSQL (e.g. Amazon RDS)

You can use a database-as-a-service like Amazon RDS for the Zulip database. The
experience is slightly degraded, in that most providers don't include useful
dictionary files in their installations, and don't provide a way to provide them
yourself, resulting in a degraded [full-text search][fts] experience around
issues dictionary files are relevant (e.g. stemming).

[fts]: ../subsystems/full-text-search.md

#### Step 1: Set up Zulip

Follow the [standard install instructions](install.md), with modified `install`
arguments:

```bash
./zulip-server-*/scripts/setup/install --certbot \
    --email=YOUR_EMAIL --hostname=YOUR_HOSTNAME \
    --puppet-classes=zulip::profile::standalone_nodb \
    --postgresql-missing-dictionaries
```

#### Step 2: Create the PostgreSQL database

Access an administrative `psql` shell on your PostgreSQL database, and
run the commands in `scripts/setup/create-db.sql` to:

- Create a database called `zulip` with `C.UTF-8` collation.
- Create a user called `zulip` with full rights on that database.
- Log in with the `zulip` user to create a schema called `zulip` in the `zulip`
  database. You might have to grant `create` privileges first for the `zulip`
  user to do this.

If you cannot run that SQL directly, you should perform the equivalent actions
in the service's web UI.

Depending on how authentication works for your PostgreSQL installation, you may
also need to set a password for the Zulip user, generate a client certificate,
or similar; consult the documentation for your database provider for the
available options.

#### Step 3: Configure Zulip to use the PostgreSQL database

In `/etc/zulip/settings.py` on your Zulip server, configure the
following settings with details for how to connect to your PostgreSQL
server. Your database provider should provide these details.

- `REMOTE_POSTGRES_HOST`: Name or IP address of the PostgreSQL server.
- `REMOTE_POSTGRES_PORT`: Port on the PostgreSQL server.
- `REMOTE_POSTGRES_SSLMODE`: [SSL Mode][ssl-mode] used to connect to the server.

[ssl-mode]: https://www.postgresql.org/docs/current/libpq-ssl.html#LIBPQ-SSL-PROTECTION

If you're using password authentication, you should specify the
password of the `zulip` user in /etc/zulip/zulip-secrets.conf as
follows:

```ini
postgres_password = abcd1234
```

Set the remote server's PostgreSQL version in `/etc/zulip/zulip.conf`:

```ini
[postgresql]
# Set this to match the version running on your remote PostgreSQL server
version = 16
```

Now complete the installation by running the following commands.

```bash
# Ask Zulip installer to initialize the PostgreSQL database.
su zulip -c '/home/zulip/deployments/current/scripts/setup/initialize-database'

# And then generate a realm creation link:
su zulip -c '/home/zulip/deployments/current/manage.py generate_realm_creation_link'
```

### Remote PostgreSQL database

This assumes two servers; one hosting the PostgreSQL database, and one hosting
the remainder of the Zulip services.

#### Step 1: Set up Zulip

Follow the [standard install instructions](install.md), with modified `install`
arguments:

```bash
./zulip-server-*/scripts/setup/install --certbot \
    --email=YOUR_EMAIL --hostname=YOUR_HOSTNAME \
    --puppet-classes=zulip::profile::standalone_nodb
```

#### Step 2: Create the PostgreSQL database server

On the host that will run PostgreSQL, download the Zulip tarball and install
just the PostgreSQL server part:

```bash
./zulip-server-*/scripts/setup/install \
    --puppet-classes=zulip::profile::postgresql

./zulip-server-*/scripts/setup/create-database
```

You will need to [configure `/etc/postgresql/*/main/pg_hba.conf`][pg-hba] to
allow connections to the `zulip` database as the `zulip` user from the
application frontend host. How you configure this is up to you (i.e. password
authentication, certificates, etc), and is outside the scope of this document.

[pg-hba]: https://www.postgresql.org/docs/current/auth-pg-hba-conf.html

#### Step 3: Configure Zulip to use the PostgreSQL database

In `/etc/zulip/settings.py` on your Zulip server, configure the following
settings with details for how to connect to your PostgreSQL server.

- `REMOTE_POSTGRES_HOST`: Name or IP address of the PostgreSQL server.
- `REMOTE_POSTGRES_PORT`: Port on the PostgreSQL server; this is likely `5432`
- `REMOTE_POSTGRES_SSLMODE`: [SSL Mode][ssl-mode] used to connect to the server.

If you're using password authentication, you should specify the
password of the `zulip` user in /etc/zulip/zulip-secrets.conf as
follows:

```ini
postgres_password = abcd1234
```

Set the remote server's PostgreSQL version in `/etc/zulip/zulip.conf`:

```ini
[postgresql]
# Set this to match the version running on your remote PostgreSQL server
version = 16
```

Now complete the installation by running the following commands.

```bash
# Ask Zulip installer to initialize the PostgreSQL database.
su zulip -c '/home/zulip/deployments/current/scripts/setup/initialize-database'

# And then generate a realm creation link:
su zulip -c '/home/zulip/deployments/current/manage.py generate_realm_creation_link'
```

## PostgreSQL vacuuming alerts

The `autovac_freeze` PostgreSQL alert from `check_postgres` is particularly
important. This alert indicates that the age (in terms of number of
transactions) of the oldest transaction id (XID) is getting close to the
`autovacuum_freeze_max_age` setting. When the oldest XID hits that age,
PostgreSQL will force a VACUUM operation, which can often lead to sudden
downtime until the operation finishes. If it did not do this and the age of the
oldest XID reached 2 billion, transaction id wraparound would occur and there
would be data loss. To clear the nagios alert, perform a `VACUUM` in each
indicated database as a database superuser (i.e. `postgres`).

See [the PostgreSQL documentation][vacuum] for more details on PostgreSQL
vacuuming.

[vacuum]: http://www.postgresql.org/docs/current/static/routine-vacuuming.html#VACUUM-FOR-WRAPAROUND
