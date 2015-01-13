# -*- coding: utf-8 -*-

from ldaplite import LdapliteObject

# --- Module global attributes
def log(*args, **kwargs):
    """Dummy log function
    Must be replace from outside with
    models.log = logger.log
    """
    pass

class groupOfNames(LdapliteObject):
    """A class for representing groups"""

    _class = ('groupOfNames',)
    _must = ['cn','o','member']
    _may = ['member']
    _rdn = ('o','o')
    _sortAttr = 'cn'

    @property
    def mailingList(self):
        """return a list of formated emails"""
        l = []
        for ob in self.dereference('member'):
            if ob.has_attr('mail'):
                l += ["%s <%s>" % (ob.attr(["cn","sn","o"]), ob.attr('mail'))]
        return l


class mozillaAbPersonAlpha(LdapliteObject):
    """A class for representing people"""

    _class = ('mozillaAbPersonAlpha','inetOrgPerson')
    _must = ['uid', 'cn', 'sn']
    _may = ['givenName','homePhone','l','mail','mobile','seeAlso','telephoneNumber']
    _rdn = ('uid','%s', lambda o: o.attr('cn').lower().replace(' ',''))
    _sortAttr = 'sn'
