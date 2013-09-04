===============================================
django-bigfoot - HTML building block for Django
===============================================

__Currently a work in progress. Please email us if you're intersted in using
it.__

django-bigfoot makes helps define HTML building blocks (e.g., forms, form
fields, tables) that can be easily be combined and rendered into HTML.

What do I want that for?!
=========================

Let's say you want to display a formset as a table. You already have a defined
style for your form fields that shows errors just like you want 'em. Well, with
bigfoot, you define a template for your form field, a template for a form
(probably just the form tag), and a template for a table. Then you do this:

    def my_view(request):
        formset = formset_factory(...)
        bigfoot_form = Form(
            Table(formset, {
                'description': FormField(A(), 'description'),
                'amount': FormField(A(), 'amount')
            })
        return render('template.html', {'elements': bigfoot_form})

Here's template.html:

    <html>
        <head></head>
        <body>{{ elements }}</body>
    </html>

Yep, that's all.

