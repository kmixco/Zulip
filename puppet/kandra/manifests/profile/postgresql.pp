class kandra::profile::postgresql inherits kandra::profile::base {

  include zulip::profile::postgresql
  include kandra::teleport::db
  include kandra::prometheus::postgresql

  $common_packages = ['xfsprogs']
  package { $common_packages: ensure => installed }

  kandra::firewall_allow{ 'postgresql': }

  zulip::sysctl { 'postgresql-swappiness':
    key   => 'vm.swappiness',
    value => '0',
  }
  zulip::sysctl { 'postgresql-overcommit':
    key   => 'vm.overcommit_memory',
    value => '2',
  }

  file { '/root/setup_disks.sh':
    ensure => file,
    owner  => 'root',
    group  => 'root',
    mode   => '0744',
    source => 'puppet:///modules/kandra/postgresql/setup_disks.sh',
  }
  exec { 'setup_disks':
    command => '/root/setup_disks.sh',
    require => Package["postgresql-${zulip::postgresql_common::version}", 'xfsprogs'],
    unless  => 'test /var/lib/postgresql/ -ef /srv/postgresql/',
  }

  file { "${zulip::postgresql_base::postgresql_confdir}/pg_hba.conf":
    ensure  => file,
    require => Package["postgresql-${zulip::postgresql_common::version}"],
    owner   => 'postgres',
    group   => 'postgres',
    mode    => '0640',
    source  => 'puppet:///modules/kandra/postgresql/pg_hba.conf',
  }
}
