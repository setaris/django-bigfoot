import logging
import re
import sys

from django.conf import settings
from django.forms.forms import BoundField
from django.template import Context
from django.template.loader import get_template
from django.utils.html import conditional_escape

import elements

def render_field(field, form, form_style, context, template, labelclass=None, layout_object=None, attrs=None):
    """
    Taken from django-crispy-forms. Renders a form field
    
    :param field: Can be a string or a Layout object like `Row`. If it's a layout
        object, we call its render method, otherwise we instantiate a BoundField
        and render it using default template 'uni_form/field.html'
        The field is added to a list that the form holds called `rendered_fields`
        to avoid double rendering fields.

    :param form: The form/formset to which that field belongs to.
    
    :param form_style: A way to pass style name to the CSS framework used.

    :template: Template used for rendering the field.

    :layout_object: If passed, it points to the Layout object that is being rendered.
        We use it to store its bound fields in a list called `layout_object.bound_fields`

    :attrs: Attributes for the field's widget
    """
    FAIL_SILENTLY = False  #getattr(settings, 'CRISPY_FAIL_SILENTLY', True)

    if not hasattr(form, 'rendered_fields'):
        form.rendered_fields = set()

    if isinstance(context, dict):
        context = Context(context)

    if hasattr(field, 'render'):
        return field.render(form, form_style, context)
    else:
        # This allows fields to be unicode strings, always they don't use non ASCII
        try:
            if isinstance(field, unicode):
                field = str(field)
            # If `field` is not unicode then we turn it into a unicode string, otherwise doing
            # str(field) would give no error and the field would not be resolved, causing confusion 
            else:
                field = str(unicode(field))
                
        except (UnicodeEncodeError, UnicodeDecodeError):
            raise Exception("Field '%s' is using forbidden unicode characters" % field)

    try:
        # Injecting HTML attributes into field's widget, Django handles rendering these
        field_instance = form.fields[field]
        if attrs is not None:
            field_instance.widget.attrs.update(attrs)
    except KeyError:
        if not FAIL_SILENTLY:
            raise Exception("Could not resolve form field '%s'." % field)
        else:
            field_instance = None
            logging.warning("Could not resolve form field '%s'." % field, exc_info=sys.exc_info())
            
    if not field in form.rendered_fields:
        form.rendered_fields.add(field)
    else:
        if not FAIL_SILENTLY:
            raise Exception("A field should only be rendered once: %s" % field)
        else:
            logging.warning("A field should only be rendered once: %s" % field, exc_info=sys.exc_info())

    if field_instance is None:
        html = ''
    else:
        bound_field = BoundField(form, field_instance, field)

        template = get_template(template)

        # We save the Layout object's bound fields in the layout object's `bound_fields` list
        if layout_object is not None:
            layout_object.bound_fields.append(bound_field)

        context.update({'field': bound_field, 'labelclass': labelclass, 'flat_attrs': flatatt(attrs or {})})
        html = template.render(context)

    return html


def flatatt(attrs):
    """
    Taken from django.core.utils 
    Convert a dictionary of attributes to a single string.
    The returned string will contain a leading space followed by key="value",
    XML-style pairs.  It is assumed that the keys do not need to be XML-escaped.
    If the passed dictionary is empty, then return an empty string.
    """
    return u''.join([u' %s="%s"' % (k.replace('_', '-'), conditional_escape(v)) for k, v in attrs.items()])

def convert_camel_case(camelstr, delim='_'):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1%s\2' % delim, camelstr)
    return re.sub('([a-z0-9])([A-Z])', r'\1%s\2' % delim, s1).lower()

def formfields(form, *fields, **kwargs):
    """ Shortcut for getting multiple form fields from the same form.

    :type  form: `django.form`
    :param form: The form where the fields are defined.

    :type  fields: `list` of `basestring`
    :param fields: (optional) A list of field names. If not fields are
    specified, all the forms fields are returned.

    :type  wrapper_class: `class`
    :param wrapper_class: (optional) The class to wrap the fields in.
    Defaults to ElementSet.

    :type  field_class: `class`
    :param field_class: (optional) The class that renders the field. Default to
    FormField.

    :returns: An instance of wrapper_class if specified. Otherwise `list`.
    """

    wrapper_class = kwargs.pop('wrapper_class', elements.ElementSet)
    field_class = kwargs.pop('field_class', elements.FormField)
    if not fields:
        fields = form.fields.keys()
    res = [field_class(form, field, **kwargs) for field in fields]
    if wrapper_class:
        res = wrapper_class(*res)
    return res

## {{{ http://code.activestate.com/recipes/496741/ (r1)
class Proxy(object):
    __slots__ = ["_obj", "__weakref__"]
    def __init__(self, obj):
        object.__setattr__(self, "_obj", obj)
    
    #
    # proxying (special cases)
    #
    def __getattribute__(self, name):
        return getattr(object.__getattribute__(self, "_obj"), name)
    def __delattr__(self, name):
        delattr(object.__getattribute__(self, "_obj"), name)
    def __setattr__(self, name, value):
        setattr(object.__getattribute__(self, "_obj"), name, value)
    
    def __nonzero__(self):
        return bool(object.__getattribute__(self, "_obj"))
    def __str__(self):
        return str(object.__getattribute__(self, "_obj"))
    def __repr__(self):
        return repr(object.__getattribute__(self, "_obj"))
    
    #
    # factories
    #
    _special_names = [
        '__abs__', '__add__', '__and__', '__call__', '__cmp__', '__coerce__', 
        '__contains__', '__delitem__', '__delslice__', '__div__', '__divmod__', 
        '__eq__', '__float__', '__floordiv__', '__ge__', '__getitem__', 
        '__getslice__', '__gt__', '__hash__', '__hex__', '__iadd__', '__iand__',
        '__idiv__', '__idivmod__', '__ifloordiv__', '__ilshift__', '__imod__', 
        '__imul__', '__int__', '__invert__', '__ior__', '__ipow__', '__irshift__', 
        '__isub__', '__iter__', '__itruediv__', '__ixor__', '__le__', '__len__', 
        '__long__', '__lshift__', '__lt__', '__mod__', '__mul__', '__ne__', 
        '__neg__', '__oct__', '__or__', '__pos__', '__pow__', '__radd__', 
        '__rand__', '__rdiv__', '__rdivmod__', '__reduce__', '__reduce_ex__', 
        '__repr__', '__reversed__', '__rfloorfiv__', '__rlshift__', '__rmod__', 
        '__rmul__', '__ror__', '__rpow__', '__rrshift__', '__rshift__', '__rsub__', 
        '__rtruediv__', '__rxor__', '__setitem__', '__setslice__', '__sub__', 
        '__truediv__', '__xor__', 'next',
    ]

    _implemented = []
    
    @classmethod
    def _create_class_proxy(cls, theclass):
        """creates a proxy for the given class"""
        
        def make_method(name):
            def method(self, *args, **kw):
                return getattr(object.__getattribute__(self, "_obj"), name)(*args, **kw)
            return method
        
        namespace = {}
        for name in cls._special_names:
            if name in cls._implemented:
                namespace[name] = getattr(cls, name)
            elif hasattr(theclass, name):
                namespace[name] = make_method(name)
        return type("%s(%s)" % (cls.__name__, theclass.__name__), (cls,), namespace)
    
    def __new__(cls, obj, *args, **kwargs):
        """
        creates an proxy instance referencing `obj`. (obj, *args, **kwargs) are
        passed to this class' __init__, so deriving classes can define an 
        __init__ method of their own.
        note: _class_proxy_cache is unique per deriving class (each deriving
        class must hold its own cache)
        """
        try:
            cache = cls.__dict__["_class_proxy_cache"]
        except KeyError:
            cls._class_proxy_cache = cache = {}
        try:
            theclass = cache[obj.__class__]
        except KeyError:
            cache[obj.__class__] = theclass = cls._create_class_proxy(obj.__class__)
        ins = object.__new__(theclass)
        theclass.__init__(ins, obj, *args, **kwargs)
        return ins

class BigfootIter(Proxy):
    """ An iterator that yields a translated version of each data item. The
    translation maps the data item into a dictionary that has the fields
    required by the table being rendered.
    """

    _implemented = ['__iter__']

    def __init__(self, data, translator, context):
        """ Initialization.

        :type  data: Queryset or anything list-like.
        :param data: The data

        :type  translator: `dict`
        :param translator: The translator provides instructions in the form of
        `Accessor`s and renderables (the dict's values) for creating a new
        dictionary with the same keys but with values that can be inserted into
        a template.

        Example:
            >>> BigfootIter(People.object.all(), {
                    'full name':
                    lambda x: '%s %s' % (x.first_name, x.last_name)
                })
        """

        super(BigfootIter, self).__init__(data)
        self.data = data
        self.translator = translator
        self.context = context

    def __iter__(self):
        for row in self.data:
            vals = dict()
            for name, trans in self.translator.items():
                rendered = False
                try:
                    # Try as an accessor
                    val = trans.resolve(row)
                    rendered = True
                except (TypeError, AttributeError):
                    pass

                if not rendered:
                    # Try as a renderable
                    trans.data = row
                    val = trans.render(**self.context)

                vals[name] = val

            yield vals

