class zulip::nginx {
  $web_packages = [
    # Needed to run nginx with the modules we use
    "nginx-full",
  ]
  package { $web_packages: ensure => "installed" }

  file { "/etc/nginx/zulip-include/":
    require => Package["nginx-full"],
    recurse => true,
    owner => "root",
    group => "root",
    mode => 644,
    source => "puppet:///modules/zulip/nginx/zulip-include-common/",
  }

  file { "/etc/nginx/nginx.conf":
    require => Package["nginx-full"],
    ensure => file,
    owner => "root",
    group => "root",
    mode => 644,
    source => "puppet:///modules/zulip/nginx/nginx.conf",
  }

  file { "/etc/nginx/fastcgi_params":
    require => Package["nginx-full"],
    ensure => file,
    owner => "root",
    group => "root",
    mode => 644,
    source => "puppet:///modules/zulip/nginx/fastcgi_params",
  }

  file { "/etc/nginx/sites-enabled/default":
    ensure => absent,
  }

  file { "/etc/supervisor/conf.d/nginx.conf":
    require => Package[supervisor],
    ensure => file,
    owner => "root",
    group => "root",
    mode => 644,
    source => "puppet:///modules/zulip/supervisor/conf.d/nginx.conf",
  }
}
