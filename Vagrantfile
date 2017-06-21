# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.provider "virtualbox" do |v|
    v.customize ["modifyvm", :id, "--memory", "2048"]
    v.customize ["modifyvm", :id, "--cpus", "2"]
    v.customize ["modifyvm", :id, "--natdnshostresolver1", "on"]
    v.customize ["modifyvm", :id, "--natdnsproxy1", "on"]
    v.customize ["modifyvm", :id, "--ioapic", "on"]
    v.customize ["modifyvm", :id, "--vram", "16"]
    v.customize ["modifyvm", :id, "--accelerate3d", "on"]
  end
  config.vm.box = "puppetlabs/centos-7.0-64-puppet"
  config.ssh.forward_agent = true
  config.vm.network :forwarded_port, host: 8000, guest: 8000
  config.vm.network :forwarded_port, host: 8080, guest: 80
  config.ssh.forward_x11 = true
  config.ssh.insert_key = false
  config.vm.network :private_network, ip: '192.168.50.50'
  config.vm.synced_folder '.', '/vagrant', nfs: true
  config.vm.provision "shell", path: "provision.sh"
end
