Instructions for Setting up PyCharm to work in your VM
======================================================

1. Download and install PyCharm Professional from https://www.jetbrains.com/pycharm/download 
   (free for students with a .edu email address).

2. Open a project from the PyCharm IDE in the directory of your Vagrant VM, e.g. ~/Vagrants/stoqsvm

3. The Professional version of PyCharm includes the Vagrant plugin. You can bring your VM up and halt
   it via the menu in Tools -> Vagrant.


### Make sure sftpd-server is properly configured in your VM

1. cd ~/Vagrants/stoqsvm_python3/ && vagrant ssh -- -X

2. sudo vi /etc/ssh/sshd_config

3. Change line from `Subsystem sftp /usr/lib/openssh/sftp-server` to `Subsystem sftp /usr/libexec/openssh/sftp-server`

4. Restart sshd:

        sudo /usr/bin/systemctl restart sshd


### Setting up PyCharm Project Interpretor and Project Structure (on MacOS)

1. From PyCharm open Preferences -> Project: stoqsvm -> Project Interpreter:
    * Click on the 3-dot icon to the right of the Project Interpreter selector
    * Check Vagrant
    * Click on the 3-dot icon to the right of Python interpreter path text box, select 'Yes' to connect to remote host
    * Navigate to '/home/vagrant/dev/stoqsgit/venv-stoqs/bin/python' and click OK
    * Click OK on the Preferences dialog window

2. Wait a few minutes for PyCharm to connect to your VM and build its project files (which are kept in the .idea directory)

3. Find the STOQS project files in the Vagrant synced folder stoqsvm/dev/stoqsgit

