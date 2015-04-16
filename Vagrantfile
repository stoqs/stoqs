# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure(2) do |config|
  config.vm.box = "base"
  config.vm.box_url = "https://github.com/2creatives/vagrant-centos/releases/download/v6.5.3/centos65-x86_64-20140116.box"
  config.ssh.forward_agent = true
  config.vm.network :forwarded_port, host: 8000, guest: 8000
  config.vm.provision "shell", path: "provision_centos.sh"
end
