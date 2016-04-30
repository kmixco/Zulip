# -*- mode: ruby -*-

VAGRANTFILE_API_VERSION = "2"

def command?(name)
  `which #{name}`
  $?.success?
end

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|

  # For LXC. VirtualBox hosts use a different box, described below.
  config.vm.box = "fgrehm/trusty64-lxc"

  # The Zulip development environment runs on 9991 on the guest.
  config.vm.network "forwarded_port", guest: 9991, host: 9991, host_ip: "127.0.0.1"

  config.vm.synced_folder ".", "/vagrant", disabled: true
  config.vm.synced_folder ".", "/srv/zulip"

  proxy_config_file = ENV['HOME'] + "/.zulip-vagrant-config"
  if File.file?(proxy_config_file)
    http_proxy = https_proxy = no_proxy = ""

    IO.foreach(proxy_config_file) do |line|
      line.chomp!
      key, value = line.split(nil, 2)
      case key
      when /^([#;]|$)/; # ignore comments
      when "HTTP_PROXY"; http_proxy = value
      when "HTTPS_PROXY"; https_proxy = value
      when "NO_PROXY"; no_proxy = value
      end
    end

    if Vagrant.has_plugin?("vagrant-proxyconf")
      if http_proxy != ""
        config.proxy.http = http_proxy
      end
      if https_proxy != ""
        config.proxy.https = https_proxy
      end
      if https_proxy != ""
        config.proxy.no_proxy = no_proxy
      end
    end
  end

  # Specify LXC provider before VirtualBox provider so it's preferred.
  config.vm.provider "lxc" do |lxc|
    if command? "lxc-ls"
      LXC_VERSION = `lxc-ls --version`.strip unless defined? LXC_VERSION
      if LXC_VERSION >= "1.1.0"
        # Allow start without AppArmor, otherwise Box will not Start on Ubuntu 14.10
        # see https://github.com/fgrehm/vagrant-lxc/issues/333
        lxc.customize 'aa_allow_incomplete', 1
      end
      if LXC_VERSION >= "2.0.0"
        lxc.backingstore = 'dir'
      end
    end
  end

  config.vm.provider "virtualbox" do |vb, override|
    override.vm.box = "ubuntu/trusty64"
    # 2GiB seemed reasonable here. The VM OOMs with only 1024MiB.
    vb.memory = 2048
  end

$provision_script = <<SCRIPT
set -x
set -e
/usr/bin/python /srv/zulip/provision.py
SCRIPT

  config.vm.provision "shell",
    # We want provision.py to be run with the permissions of the vagrant user.
    privileged: false,
    inline: $provision_script
end
