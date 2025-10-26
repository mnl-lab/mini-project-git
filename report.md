# Tp 5 report

## Exercise 1
- checking installation and configuring identity
```powershell
PS C:\Users\utilisateur> git version
git version 2.51.0.windows.2
PS C:\Users\utilisateur> git config --global user.name "mnl"
PS C:\Users\utilisateur> git config --global user.email "manalzaidi2005@gmail.com"
```
- creating a local repository
```bash
mnl@PC2656:/mnt/c/Users/utilisateur/s5/swe/code/tp5$ cd tp-git
mnl@PC2656:/mnt/c/Users/utilisateur/s5/swe/code/tp5/tp-git$ git init
hint: Using 'master' as the name for the initial branch. This default branch name
hint: is subject to change. To configure the initial branch name to use in all
hint: of your new repositories, which will suppress this warning, call:
hint:
hint:   git config --global init.defaultBranch <name>
hint:
hint: Names commonly chosen instead of 'master' are 'main', 'trunk' and
hint: 'development'. The just-created branch can be renamed via this command:
hint:
hint:   git branch -m <name>
Initialized empty Git repository in /mnt/c/Users/utilisateur/s5/swe/code/tp5/tp-git/.git/
```
- creating README file and committing changes
```bash
/tp-git/.git/
mnl@PC2656:/mnt/c/Users/utilisateur/s5/swe/code/tp5/tp-git$ echo "# Git and Github Lab" > README.md
mnl@PC2656:/mnt/c/Users/utilisateur/s5/swe/code/tp5/tp-git$ git add README.md
mnl@PC2656:/mnt/c/Users/utilisateur/s5/swe/code/tp5/tp-git$ git commit -m "Initial commit: add README"
[master (root-commit) f841356] Initial commit: add README
 Committer: mnl-lab <mnl@PC2656.localdomain>
Your name and email address were configured automatically based
on your username and hostname. Please check that they are accurate.
You can suppress this message by setting them explicitly:

    git config --global user.name "Your Name"
    git config --global user.email you@example.com

After doing this, you may fix the identity used for this commit with:

    git commit --amend --reset-author

 1 file changed, 1 insertion(+)
 create mode 100644 README.md
 ```
 -> What does git init do? 
- `git init` initializes a new Git repository in the current directory. It creates a hidden `.git` folder that contains all the necessary metadata and version control information for the repository.
-> What is stored inside the .git folder?
- The `.git` folder contains various subdirectories and files that store the repository's configuration, commit history, branches, tags, and other essential data required for version control operations. Key components include:
  - `HEAD`: Points to the current branch reference.
  - `config`: Contains repository-specific configuration settings.
  - `objects/`: Stores all the content of the files and commits in a compressed format.
  - `refs/`: Contains references to branches and tags.
  - `index`: Staging area for changes before committing.