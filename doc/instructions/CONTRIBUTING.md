Instructions for contributing to the STOQS project
==================================================

You are encouraged to contribute to STOQS!

Basic Unix, Python (server-side), JavaScipt (client-side), and Shell programming skills are required to effectively contribute. 
There are great resources for learning these skills at https://software-carpentry.org.
The good news is that Unix system administration skills are no longer required as `vagrant up --provider virtualbox` takes care of installing all the required software.

### Steps to Contribute
 
1. Build a development Linux system -- the Vagrantfile installation saves a lot of time and frustration in doing this

2. Fork the repository after logging into GitHub by clicking on the Fork button at https://github.com/stoqs/stoqs

3. Generate SSH keys on your development system following the instructions at https://help.github.com/articles/generating-ssh-keys/

4. Clone your fork to a working directory on your development system using the SSH version of the clone URL:

        git clone git@github.com:<your_github_id>/stoqs.git stoqsgit

   Replace \<your_github_id\> with your GitHub ID. If you built a development system from the Vagrantfile you may want to first remove the ~/dev/stoqsgit directory created during that process.

5. Configure your Python virtual environment and run the tests (these steps are done as part of the original Vagrant installation, they need to be executed because you re-cloned the repository - your working directory - in the previous step):

        cd stoqsgit
        git checkout django17upgrade
        export PATH="/usr/local/bin:$PATH"
        virtualenv venv-stoqs
        source venv-stoqs/bin/activate
        ./setup.sh
        ./test.sh <stoqsadm_pw>

6. Set up remote upstream:

        git remote add -f upstream git://github.com/stoqs/stoqs.git

#### Contributing follows a typical GitHub workflow:

1. cd into your working directory, e.g.:

        cd ~/dev/stoqsgit

2. Create a branch for the new feature: 

        git checkout master
        git checkout -b my_new_feature

3. Work on your feature; add and commit as you write code and test it. (Creating a new branch is not strictly necessary, 
but it makes it easy to delete your branch when the feature has been merged into upstream, diff your branch 
with the version that actually ended in upstream, and to submit pull requests for multiple features (branches)).

Before pushing the commits of your new feature please run `./test.sh` to make sure the test coverage has not decreased.
Another way to state this is: Be sure to write a test for your new feature in stoqs/stoqs/tests.

4. Push the new branch to your fork on GitHub:

        git push origin my_new_feature

5. Share your contribution with others by issuing a [pull request](https://help.github.com/articles/using-pull-requests/): Click Pull Request button on GitHub

#### Useful Commands

If a lot of changes have happened upstream you can replay your local changes 
on top of these, this is done with `rebase`, e.g.:

    git fetch upstream
    git rebase upstream/master

or 
    `git rebase upstream/<branch_name>`, if a lot of upstream development is happening on another branch 

