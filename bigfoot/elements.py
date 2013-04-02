import re

from django.core.exceptions import ImproperlyConfigured
from django.template import RequestContext
from django.template.loader import render_to_string
from django.template.defaulttags import CsrfTokenNode
from django.utils.datastructures import SortedDict
from django.utils.html import escape
from django.utils.safestring import mark_safe

import django_tables2 as tables

from .utils import BigfootIter
from .utils import render_field
from .utils import convert_camel_case
from .utils import flatatt

__all__ = ('Element', 'Link', 'TemplateElement', 'FormField', 'ElementSet',
    'FormFieldSet', 'Form', 'Table')

class RenderableMixin(object):
    data = None

    def render(self, **kwargs):
        raise ImproperlyConfigured('Subclass must implement render.')

    def __unicode__(self):
        res = self.render()
        return res

    def __str__(self):
        return unicode(self).encode('utf-8')

    def get(self, attr):
        """ Returns the requested attribute or, if the value of the attribute
        is a callable or accessor, the resolved value.
        """

        val = getattr(self, attr)
        if self.data:
            # First, see if we can call resolve()
            try:
                return val.resolve(self.data)
            except (AttributeError, TypeError):
                pass

            # Second, see if it's callable
            try:
                return val(self.data)
            except TypeError:
                try:
                    return val()
                except TypeError:
                    pass

        return val

class Element(RenderableMixin):
    tag = None
    attrs = None
    inner = ""
    __can_be_lazy = ('attrs', 'tag', 'inner', 'html')

    def __init__(self, **kwargs):
        self.attrs = kwargs.get('attrs', {})
        self.tag = kwargs.get('tag')
        self.inner = kwargs.get('inner', self.inner)
        self.html = kwargs.get('html')

    def get_element_template(self, tag):
        """ Renders a string template for the html element from the tag.

        :tag: For example, '<span/>'. <span> would be incorrect as it would not
        support inner HTML or an end tag.
        """

        tag = self.get('tag')
        if tag is None:
            return '%(inner)s'

        tag_check = re.match('^\s*<\s*(?P<tag>[\w:]*)\s*(?P<end_tag>\/?)\s*>\s*$', tag)
        if tag_check is None:
            raise ValueError('tag must be a valid HTML element.')

        tag = tag_check.group('tag')
        has_end_tag = tag_check.group('end_tag') == '/'

        template = '<%s %s>' % (tag, '%(attrs)s')
        if has_end_tag:
            template += '%s</%s>' % ('%(inner)s', tag)

        return template

    def render(self, **kwargs):
        template = self.get_element_template(self.get('tag'))
        return mark_safe(template % {
            'attrs': self.render_attrs(),
            'inner': self.render_inner()
        })

    def render_attrs(self):
        return " ".join(['%s="%s"' % (key, val) for key, val in
            self.get('attrs').items()])

    def render_inner(self):
        html = self.get('html')
        if html:
            # coerce to string in case the html is a bigfoot element
            return unicode(html)
        else:
            return escape(self.get('inner'))

class Link(Element):
    def __init__(self, text, href, attrs=None):
        attrs = attrs or {}
        self.href = href
        super(Link, self).__init__(inner=text, tag='<a/>', attrs=attrs)

    def get(self, attr):
        res = super(Link, self).get(attr)
        if attr == 'attrs':
            res['href'] = self.get('href')
        return res

class Button(Element):
    def __init__(self, **kwargs):
        attrs = kwargs.get('attrs', {})
        attrs.update({'type': 'submit'})
        kwargs['attrs'] = attrs
        kwargs['tag'] = '<input/>'
        super(Button, self).__init__(**kwargs)

class TemplateElement(RenderableMixin):
    template_name = None
    context = None
    request = None
    add_to_context = dict()
    attrs = None

    def __init__(self, template_name=None, context=None, request=None,
    attrs=None):
        context = context or {}
        self.request = request
        self.context = context
        self.template_name = template_name
        self.attrs = attrs or {}

    def render(self, **kwargs):
        context = self.get_context_data(**kwargs)
        return mark_safe(render_to_string(self.get_template_name(), context))

    def get_template_name(self):
        template_name = self.get('template_name')
        if template_name:
            return template_name
        return 'bigfoot/%s.html' % self.__class__.__name__.lower()

    def get_context_data(self, **kwargs):
        context = dict(self.get('context'), **kwargs)

        # Add class attributes to context if anything is listed in
        # add_to_context
        for attr in self.add_to_context:
            val = self.get(attr)
            key = '%s_%s' % (self.__class__.__name__.lower(), attr)
            context[key] = val

        context['attrs'] = mark_safe(flatatt(self.attrs))

        # Return a request context if we have the request
        if self.request:
            return RequestContext(self.request, context)


        return context

class Table(TemplateElement):
    def __init__(self, data, columns, *args, **kwargs):
        self.table_class = kwargs.pop('table_class', tables.Table)
        self.table_attrs = kwargs.pop('table_attrs', {})
        super(Table, self).__init__(*args, **kwargs)
        self.data = data
        self.columns = columns

    def render(self, **kwargs):
        context = self.get_context_data(**kwargs)

        # Create a table renderer
        attrs = SortedDict()
        for col in self.columns.keys():
            attrs[col] = tables.Column(orderable=False)
        Meta = getattr(self.table_class, 'Meta',
            type('Meta', tuple(), {'attrs': {}}))
        Meta.attrs.update(self.table_attrs)
        attrs['Meta'] = Meta
        TableClass = type('BigFootTable', (self.table_class,), attrs)

        data = BigfootIter(self.data, self.columns, context)
        table = TableClass(data)
        context['table'] = table
        return mark_safe(render_to_string(self.get_template_name(), context))

class FormField(TemplateElement):
    add_to_context = ('show_label',)

    def __init__(self, form, field_name, **kwargs):
        self.form = form
        self.name = field_name
        self.show_label = kwargs.pop('show_label', True)
        super(FormField, self).__init__(**kwargs)

    def render(self, **kwargs):
        res = render_field(self.get('name'), self.get('form'), "",
            context = self.get_context_data(**kwargs),
            template = self.get_template_name())
        return res

class FormFields(TemplateElement):
    template_name = 'bigfoot/elementset.html'

    def __init__(self, form, fields, *args, **kwargs):
        self.form = form
        self.fields = fields
        super(FormFields, self).__init__(*args, **kwargs)

    def render(self, **kwargs):
        res = ""
        for field in self.get('fields'):
            res += render_field(self.get('name'), self.get('form'), "",
                context = self.get_context_data(**kwargs),
                template = self.get_template_name())
        return res

class ElementSet(TemplateElement):
    elements = None

    def __init__(self, *elements, **kwargs):
        self.elements = list(elements)
        super(ElementSet, self).__init__(**kwargs)

    def render(self, **kwargs):
        rendered_set = []
        for element in self.elements:
            element.data = self.data or element.data
            rendered_set.append(element.render(**self.context))
        return super(ElementSet, self).render(elements=rendered_set, **kwargs)

    def find(self, **kwargs):
        """ Search for child elements using specified search criterion. The
        following kwargs are supported:

            :element_type: A class of element to search for (e.g., FormField)
        """

        matches = []
        element_type = kwargs.get('element_type')
        if not element_type:
            raise AttributeError('At least one search parameter must be ' +
                'specified.')
        for element in self.elements:
            if isinstance(element, element_type):
                matches.append(element)
            elif isinstance(element, ElementSet):
                matches.extend(element.find(**kwargs))
        return matches

class FormFieldSet(ElementSet):
    def render(self, **kwargs):
        return super(FormFieldSet, self).render(**kwargs)

class Form(FormFieldSet):
    add_to_context = ('method', 'action', 'allow_files')

    def __init__(self, *fields, **kwargs):
        self.method = kwargs.pop('method', 'POST')
        self.action = kwargs.pop('action', '')
        self.allow_files = kwargs.pop('allow_files', False)
        super(Form, self).__init__(*fields, **kwargs)

