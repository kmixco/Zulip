class zulip_ops::loadbalancer {
  include zulip_ops::base
  include zulip::nginx
  include zulip::camo

  file { '/etc/nginx/sites-available/loadbalancer':
    ensure  => file,
    require => Package['nginx-full'],
    owner   => 'root',
    group   => 'root',
    mode    => '0644',
    source  => 'puppet:///modules/zulip_ops/nginx/sites-available/loadbalancer',
    notify  => Service['nginx'],
  }

  file { '/etc/motd':
    ensure => file,
    owner  => 'root',
    group  => 'root',
    mode   => '0644',
    source => 'puppet:///modules/zulip_ops/motd.lb0',
  }

  file { '/etc/nginx/sites-enabled/loadbalancer':
    ensure  => 'link',
    require => Package['nginx-full'],
    target  => '/etc/nginx/sites-available/loadbalancer',
    notify  => Service['nginx'],
  }

  # Can be removed if you see it deployed:
  file { '/etc/cron.d/log2zulip':
    ensure => absent,
  }
}
