# -*- coding: utf-8 -*-
__author__ = "FrViPofm"
__version__ = "0.0.1-dev"
__license__ = "GPL License"

# --- Modules
from datetime import datetime
import ldap
import ldif
import inspect
from StringIO import StringIO
from ldap.cidict import cidict
# --- Exceptions
class LdapliteNoConnexion(Exception): pass
class ObjectDoesNotExist(Exception): pass

# --- Module global attributes
_l=None
_history = []
def logger(*args, **kwargs):
    """Dummy log function
    Must be replace from outside with
    models.log = logger.log
    """
    pass

models = None

def ldapize(cred, who, host="localhost", port=389, base="o=addressbook,dc=lan"):
    """
    param : host
    param : port
    param : base
    param : who
    param : cred
    
    """
    globals()["_l"] = Ldaplite(base)
    logs = open('trace.txt','w')
    try:
        l = ldap.initialize("ldap://%(host)s:%(port)s/" % {'host':host, 'port':port}, trace_level=2, trace_file=logs)
        l.simple_bind_s(who, cred)
        globals()["_history"] += ["connected at %s" % host]
    except ldap.LDAPError as error_message:
        raise LdapliteNoConnexion(error_message)
    
    
    globals()["_l"].conx["default"] = l
    globals()["_l"].base = base
    globals()["search"] = _l.search
    globals()["_history"] += ["""init ldaplite
    who: %(who)s
    host: %(host)s
    base: %(base)s
    """ % {
        'who': who,
        'host': host,
        'base': globals()["_l"].base
    }]

class Ldaplite(object):

    objectClass = {}
    UNCHANGED = 0
    MODIFIED = 1
    NEW = 2
    
    def __init__(self, base=False):
        self.conx={}
        self.base= base or ''
        self._logger = globals()["logger"]
#        self._log("Ldaplite models %s" % globals()["models"])
        self.loadObjectClasses(models = globals()["models"])

    def __del__(self):
        self.conx["default"].unbind()
    
    def search(self, dn=False, filter='(objectclass=*)', attrs=['*']):
        dn = dn or self.base
        self._logger.log("search %(filter)s objects at %(dn)s " % {'dn':dn, 'filter': filter})
        
        try:
            raw = self.conx["default"].search_s( dn, ldap.SCOPE_SUBTREE, filter, attrs )
        except ldap.NO_SUCH_OBJECT as e:
            self._logger.log("No %(filter)s object at %(dn)s " % {'dn':dn, 'filter': filter}, level="warn")
            raise ldap.NO_SUCH_OBJECT("No %(filter)s object at %(dn)s " % {'dn':dn, 'filter': filter})
        except ldap.INVALID_DN_SYNTAX as e:
            self._logger.log("Invalid dn syntax %(filter)s object at %(dn)s " % {'dn':dn, 'filter': filter}, level="warn")
            raise ldap.INVALID_DN_SYNTAX("No %(filter)s object at %(dn)s " % {'dn':dn, 'filter': filter})
#            raise e
        res = LdapliteSet(_l = self)

        if type(raw) == tuple and len(raw) == 2 :
            (code, arr) = raw
        elif type(raw) == list:
            arr = raw

        if len(raw) == 0:
            return res

        for item in arr:
            res.append( LdapliteObject.factory(item, _l=self) )

        return res

    def add(self, obj):
        """add a new object to the base"""
        
        try:
            self._logger.log("adding object %s" % (obj.dn, ))
#            res = self.conx["default"].add_s(obj.dn, obj.attrs)
        except ldap.LDAPError as e:
            self._logger.warn("Unable to add object %s" % (obj.dn, ), 'Err')
        return obj

    def loadObjectClasses(self, models = globals()["models"]):
        if globals()["models"]:
            for item in models.__dict__:
                if hasattr(models.__dict__[item], '_rdn'):
                    cls = models.__dict__[item]
                    self._logger.log("loadObjectClasses loading %s objectClass" % str(cls._class))
                    Ldaplite.objectClass[cls._class[0]] = cls
        # fallback objectClass
        Ldaplite.objectClass[LdapliteObject._class] = LdapliteObject

class LdapliteSet(list):
    """A class to model and manage a search result of ldaplite
    """
    
    def __init__(self, *args, **kwargs):
        if "_l" in kwargs:
            self._l = kwargs["_l"]
            del kwargs["_l"]
        super(LdapliteSet, self).__init__(*args, **kwargs)
        self._logger = globals()["logger"]

    def sort(self, **kwargs):
        from operator import attrgetter
        try:
            reverse = kwargs['reverse']
            del kwargs['reverse']
        except KeyError:
            reverse = False
        if len(kwargs):
            if 'property' in kwargs:
                self._logger.log("sort by %(kwargs)s %(n)s objects" % {'kwargs':str(kwargs), 'n':len(self)})
                super(LdapliteSet, self).sort(key=attrgetter(kwargs['property']),
                                              reverse=reverse)
        else:
            self._logger.log("sort default %(n)s objects" % {'kwargs':str(kwargs), 'n':len(self)})
            super(LdapliteSet, self).sort(key=attrgetter('sortVal'),
                                          reverse=reverse)
        return self

    def isort(self, *args, **kwargs):
        "no case sort"
        from operator import attrgetter
        try:
            reverse = kwargs['reverse']
            del kwargs['reverse']
        except KeyError:
            reverse = False
        
        if len(args):
            f = lambda x : x.attr(y).lower
            super(LdapliteSet, self).sort(cmp=f)
        
        if len(kwargs):
            if 'property' in kwargs:
                super(LdapliteSet, self).sort(key=attrgetter(kwargs['property']),
                                              reverse=reverse)
        else:
            super(LdapliteSet, self).sort(key=lambda obj : obj.sortVal.lower(),
                                          reverse=reverse)
        return self

    def filter(self, **kwargs):
        if len(kwargs) == 0:
            return self
        if 'dn' in kwargs:
            dn = kwargs['dn']
            del kwargs['dn']
            return LdapliteSet([obj for obj in self if obj.dn != dn]).filter(**kwargs)
        filtered = []
        for key, val in kwargs:
             filtered += [obj for obj in self if (not self.has_attr(key)) or val not in list(self.avals(key))]
        return LdapliteSet(filtered)

    @property
    def dereference(self, attr):
        return LdapliteSet([obj.dereference(attr) for obj in self])

    @property
    def related(self):
        return LdapliteSet([obj.related for obj in self])

    @property
    def pretty(self):
        return "\n".join([obj.pretty for obj in self])

    @property
    def as_ldif(self):
        return "\n\n".join([obj.as_ldif for obj in self])

class LdapliteAttribute(list):
    """A class to contains attribute values"""
    _validators = ()

    def __init__(self, value):
        super(LdapliteSet, self).__init__(value)

    def is_valid(self):
        return True

class LdapliteObject(object):
    # from http://www.packtpub.com/article/python-ldap-applications-ldap-opearations
    """A class to model ldaplite objects.
    """

    _class = ('organizationalUnit',)
    _must = ['ou']
    _may = ['l']
    _rdn = ('ou')
    dn = ''
    _sortAttr = 'dn'
    

    def __init__(self, dn, attrs, _l=False, state = Ldaplite.UNCHANGED):
        """Create a new LDAPSearchResult object."""
        self._l = _l or globals()["_l"]
        self._logger = globals()["logger"]
        self.attrs = cidict(attrs)
        self._state = state
#        self._log()
        if dn:
            self.dn = dn
        else:
            return


    def __del__(self):
        """auto-save changed or created objects"""
        self._logger.log('LdapliteObject.__del__ state: %s' % self._state)
        if self._state == Ldaplite.NEW:
            obj = globals()['_l'].add(self)

    @staticmethod
    def factory(entry_tuple, _l=False, state = Ldaplite.UNCHANGED):
        """Create a new LdapliteObject subclass object"""
        (dn, attrs) = entry_tuple
        if not _l:
            _l = globals()["_l"]

#        globals()["log"]("factory Ldaplite.objectClass %s" % Ldaplite.objectClass)
        for cls in attrs['objectClass']:
#            globals()["logger"].log("cls %s" % cls)
            if cls in Ldaplite.objectClass:
#                globals()["logger"].log("found cls %s" % cls)
                return Ldaplite.objectClass[cls](dn, attrs, _l)
        #fallback
        return LdapliteObject(dn, attrs, state)

    @staticmethod
    def receive(cls, dn, form):
        """Create a new LdapliteObject subclass object from form query"""

        attrs = {
            'objectClass': [],
        }
        dn = dn or form.get(dn)
        globals()["logger"].log("receive Ldaplite.objectClass %s" % Ldaplite.objectClass[cls]._class)
        globals()["logger"].log("receive dn %s" % dn)
        objectClass = Ldaplite.objectClass[cls]
        attrs['objectClass'] = objectClass._class
        
        
        for attr in objectClass._must:
            globals()["logger"].log("receive look for %s attr" % attr)
            if attr in form:
                attrs[attr] = getattr(form, attr)

        if cls in Ldaplite.objectClass:
            globals()["logger"].log("receive found cls %s %s attrs" % (cls, attrs))
            return Ldaplite.objectClass[cls](dn, attrs)
        #fallback
        return LdapliteObject.factory((dn, attrs), state = ldaplite.NEW)

    def get_all(self):
        """Get a dictionary of all attributes.
        get_attributes()->{'name1':['value1','value2',...], 
				'name2: [value1...]}
        """
        return self.attrs

    def set_all(self, attr_dict):
        """Set the list of attributes for this record.

        The format of the dictionary should be string key, list of
        string alues. e.g. {'cn': ['M Butcher','Matt Butcher']}

        set_attrs(attr_dictionary)
        """

        self.attrs = cidict(attr_dict)

    def has_attr(self, attr_name):
        """Returns true if there is an attribute by this name in the
        record.
        has_attr(string attr_name)->boolean
        """
        return self.attrs.has_key( attr_name )


    def has_attrs(self, **args):
        """Returns true if the record has attributes according to the given parameters set :
        each passed arg must be a str or a list of str : has_attrs return False if no str is an attribute
        has_attr return True if the record has at least one attribute found in each passed arg
        The schema is arg[0] and arg[1] and ... and arg[n]
        and in each arg str[0] or str[1] or ... or str[n]
        has_attr(list of list of attr_name)->boolean
        """
        rs = True
        for arg in args:
            if arg.__class__.__name__ == 'str':
                rs = rs and self.has_attr(arg)
            elif arg.__class__.__name__ == 'list':
                r = False
                for a in arg:
                    r = r or self.has_attr(arg)
                rs = rs and r
        return rs

    def has_class(self, class_name):
        """Returns true if there is one of classes by this name in the
        record.
        has_class(string|tuple class_name)->boolean
        """
        avals = map(lambda x :x.lower(),self.get_avals("objectClass"))
        if class_name.__class__.__name__ == 'str':
            return class_name.lower() in avals
        r = False
        for c in (class_name):
            r = r or c.lower() in avals
        return r

    def get_avals(self, key):
        """Get a list of attribute values.
        get_attr_vals(string key)->['value1','value2']
        """
        return self.attrs[key]

    def get_attrs(self):
        """Get a list of attribute names.
        get_attr_names()->['name1','name2',...]
        """
        return self.attrs.keys()

    def attr(self, *args, **kwargs):
        """Polymorph function
        If call without argument, return a set of all arguments
                see get_all
        if call with one unnamed argument:
            if the argument is a string:
                returns the coresponding value or list of values
            if the argument is a list:
                returns the first valid corresponding value or list of values
            if the argument is a dict:
                shortcut for settings args
                see above
        if call with named argument :
            shortcut for settings args
            Not implemented
        get_attr_names()->['name1','name2',...]
        """
        try:
            fallback = kwargs["fallback"]
        except KeyError:
            fallback = None
#        self._log('attr fallback "%s" of %s' % (str(fallback), self.dn))
#        self._log('attr args "%s" of %s' % (str(args), self.dn))
#        self._log('attr kwargs "%s" of %s' % (str(kwargs), self.dn))
        if len(args) == 0 and len(kwargs) == 0:
            return self.get_all()

        if len(args) == 1:
            if args[0].__class__.__name__ == 'dict':
                # dict object: self call with expanded args
                return self.attr(**args[0])
            if args[0].__class__.__name__ == 'str' and self.has_attr(args[0].lower()):
                # str arg: return value or list of values
                if len(self.get_avals(args[0].lower())) == 1 :
                    return self.get_avals(args[0].lower())[0]
                return self.get_avals(args[0].lower())
            if args[0].__class__.__name__ == 'list':
                # list arg: self call with arg
                for arg in args[0]:
                    self._logger.log("attr %(attr)s of %(dn)s" %{'attr':arg,'dn':self.dn})
                    if self.has_attr(arg.lower()):
                        return self.attr(arg)
                return False if fallback == None else fallback

#                TODO: kwargs
        
#            if len(kwargs) > 0 and self.has_attr(args[0].lower()):
#                if len(self.get_avals(args[0].lower())) == 1 : return self.get_avals(args[0].lower())[0]
#                return self.get_avals(args[0].lower())
        return False if fallback == None else fallback

    @property
    def fields(self):
        fields = ()
        return fields
        

    def dereference(self, attr):
        """
        """
        self._logger.log('dereference attr "%s" of %s' % (str(attr), self.dn))
        if self.has_attr(attr):
            self._logger.log('dereference has_attr %s of %s' % (str(attr), self.dn))
            dns = self.attr(attr)
            self._logger.log('dereference dns %s of %s' % (str(dns), self.dn))
            if dns.__class__.__name__ == "str":
                dns = [dns]
            objects = LdapliteSet( _l = self)
            for dn in dns:
                self._logger.log('dereference get dn %s of %s' % (dn, self.dn))
                obj = globals()['_l'].search(dn=dn, attrs=None)
                if len(obj):
                    objects+= obj
            self.attr({attr:objects})
            return objects
        return []

    def related(self,attrs=['member','seealso']):
        """ Returns a ldapliteSet of objects having attributes pointing to self
        Inverse of self.dereference
        """
        objects = []
        if attrs.__class__.__name__ == "str":
            # single attr
            filt = '(%(attr)s=%(dn)s)' % {'attr':attrs,'dn':self.dn}
        else:
            filt = "(|%s)" % "".join(['(%(attr)s=%(dn)s)' % {'attr':attr,'dn':self.dn} for attr in attrs])
        res = globals()['_l'].search(filter=filt)
        return res

    def get_dn(self):
        """Get the DN string for the record.
        get_dn()->string dn
        """
        return self.dn

    @property
    def mainClass(self):
        return self._class[0]

    @property
    def sortVal(self):
        """Get the value for sorting"""
#        self._logger.log(u"sortVal %(attr)s %(val)s %(dn)s" % {'attr':self._sortAttr,'val': self.attr(self._sortAttr), 'dn':self.dn})
        return self.attr(self._sortAttr)

    @property
    def pretty(self):
        """Create a nice string representation of this object.
        pretty_print()->string
        """
        st = "DN: " + self.dn + "\n"
        try:
            st += inspect.getsource(self._rdn[-1])
        except Exception:
            st += str(self._rdn[0])
        for a, v_list in self.attrs.iteritems():
            st += "".join(["  %s: %s\n" %(a,v) for v in v_list])
        return st

    @property
    def pretty_html(self):
        """Create a nice html representation of this object.
        pretty_print()->string
        """
        st = "<h3>dn: " + self.dn + "</h3><dl>"
        for attr, val_list in self.attrs.iteritems():
            st += "<dt>%s</dt>\n" % attr
            if isinstance(st, basestring):
                st += "<dd>%s</dd>\n" % val_list
            else:
                st += "".join(["<dd>%s</dd>\n" % val for val in val_list])
        return st + '</dl>'

    @property
    def as_ldif(self):
        """Get an LDIF representation of this record.
        to_ldif()->string
        """
        out = StringIO()
        ldif_out = ldif.LDIFWriter(out)
        ldif_out.unparse(self.dn, self.attrs)
        return out.getvalue()


class LdaplitePlugin(object):
    """Bottle plugin for Ldaplite"""
    name = "ldaplite"
    api = 2

    def __init__(self,
                cred,
                who,
                host="localhost",
                port=389,
                base="o=addressbook,dc=lan"):
        self.cred = cred
        self.who = who
        self.host = host
        self.port = port
        self.base = base

    def setup(self, app):
        ldapize(
            who = self.who,
            cred= self.cred,
            host= self.host,
            port= self.port,
            base= self.base
        )

    def apply(self, callback, ctx):
        conf = ctx.config.get("ldaplite") or {}
        import traceback as tb
#        import bottle
        def wrapper(*args, **kwargs):
            
            try:
                ret_value = callback(*args, **kwargs)
            except LdapliteNoConnexion as e:
                raise(bottle.HTTPError(500, "Database Error", e, tb.format_exc())) 
            return ret_value
        return wrapper
