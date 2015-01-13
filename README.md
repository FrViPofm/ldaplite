# ldaplite
Bottlepy plugin for LDAP back end.

Ispired from [**Macaron**](https://github.com/nobrin/macaron), ldaplite is a [**Bottle**](http://bottlepy.org/) plugin for **ldap**.

As of now, ldaplite is reas only. It is actualy a proof of concept. But it is runing on my own computer.

As Macaron and Bottle *ldaplite* want be as easy as possible.

## The files

The main file is the *ldaplite.py* that implemente the plugin.

The second file *model.py* is the models declarations. *Kind of* Macaron's model.

This file contains two models :

groupOfNames
: a model for groups

mozillaAbPersonAlpha
: a model that is compatible with *Thunderbird*
