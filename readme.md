# appserver-template 12.0
This repository is configured to build an Odoo 12 appserver using buildout and the anybox.recipe.odoo.

# Licence
Files in this repository are Licensed under the LGPL and A-GPL Licence.

# USAGE
Please only update **[odoo]** part.
 
## VERSION
This will select which version of Odoo to use.
Update the last part of version line to select the Odoo branch to pull.
In Example below, the version is 12.0
```
version = git http://github.com/odoo/odoo.git odoo 12.0
```

## ADDONS
Allow to add custom addons by setting the repository where to fetch them.
One line per repository
The line is composed in multiple parts to set, used to fetch into a directory

- It starts with the kind of repository to use:
     * `local`: local folder
     * `git`: Git repository
     * `bzr`: Bazaar repository
     * ...
- Then, set:
     * the folder if type is local
     * the repository, otherwise
- Next (except for local type), set the folder where the repository will be stored
- Finally (except for local type), write the name of the branch to fetch

Example:
```
git https://github.com/OCA/server-tools.git parts/community/addons-oca-server-tools 12.0
```

### EGGS
Here a set the python libraries to install.
Just add a new line per lib
