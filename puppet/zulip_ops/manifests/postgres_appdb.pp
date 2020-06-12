class zulip_ops::postgres_appdb {
  include zulip_ops::postgres_common
  include zulip::postgres_appdb_tuned

  file { "/etc/postgresql/${zulip::base::postgres_version}/main/pg_hba.conf":
    ensure  => file,
    require => Package["postgresql-${zulip::base::postgres_version}"],
    owner   => 'postgres',
    group   => 'postgres',
    mode    => '0640',
    source  => 'puppet:///modules/zulip_ops/postgresql/pg_hba.conf',
  }
}
