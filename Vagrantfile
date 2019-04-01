# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.provider "virtualbox" do |v|
    v.customize ["modifyvm", :id, "--memory", "3072"]
    v.customize ["modifyvm", :id, "--cpus", "2"]
    v.customize ["modifyvm", :id, "--natdnshostresolver1", "on"]
    v.customize ["modifyvm", :id, "--natdnsproxy1", "on"]
    v.customize ["modifyvm", :id, "--ioapic", "on"]
    v.customize ["modifyvm", :id, "--vram", "16"]
  end
  config.vm.box = "bento/centos-7.5"
  config.ssh.forward_agent = true
  config.vm.network :forwarded_port, host: 8008, guest: 8000
  config.vm.network :forwarded_port, host: 8080, guest: 8080
  config.vm.network :forwarded_port, host: 8887, guest: 8888
  config.vm.network :forwarded_port, host: 80, guest: 80
  config.ssh.forward_x11 = true
  config.ssh.insert_key = false
  config.vm.network :private_network, ip: '192.168.50.50'
  # Comment out next line if your host doesn't support NFS file serving
  config.vm.synced_folder '.', '/vagrant', nfs: true,  mount_options: ['tcp', 'fsc' ,'actimeo=300']
  config.vbguest.auto_update = false
  config.vm.provision "shell", path: "provision.sh"
end
