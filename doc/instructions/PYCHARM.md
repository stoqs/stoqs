Instructions for Setting up PyCharm to work in your VM
======================================================

1. Download and install PyCharm Professional from https://www.jetbrains.com/pycharm/download 
   (free for students with a .edu email address).

2. Open a project from the PyCharm IDE in the directory of your Vagrant VM, e.g. ~/Vagrants/stoqsvm

3. The Professional version of PyCharm includes the Vagrant plugin. You can bring your VM up and halt
   it via the menu in Tools -> Vagrant.


### Setting up PyCharm Project Interpretor and Project Structure (on MacOS)

1. From PyCharm, open Preferences -> Project: stoqsvm [1] -> Project Interpreter:
    * Click on the 3-dot icon to the right of the Project Interpreter selector
    * Select 'Add Remote'
    * Check Vagrant
    * Ensure that the Vagrant Instance Fold... is pointing to the correct path
    * Click on the 3-dot icon to the right of Python interpreter path text box, select 'Yes' to connect to remote host
    * Navigate to '/vagrant/dev/stoqsgit/venv-stoqs/bin/python' and click OK
    * Click OK on the Preferences dialog window

2. Wait a few minutes for PyCharm to connect to your VM and build its project files (which are kept in the .idea directory)

3. From PyCharm, open Preferences -> Project: stoqsvm [1] -> Project Scructure:
    * Navigate to dev/stoqsgit/stoqs and right-click on it
    * Select 'Sources'

4. Find the STOQS project files in the Vagrant synced folder dev/stoqsgit

5. You may now proceed using either PyCharm or the command line in the VM to work on the STOQS code base


[1]: Your virtual machine directory may have a different name, e.g. 'stoqsvm_python3'
