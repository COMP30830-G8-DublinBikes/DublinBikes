from jinja2 import Template

tpl = """
<html>
    <head>
        <title>{{ title }} - microblog</title>
    </head>
    <body>
        <h1>Hello, {{ user.nickname }}!</h1>
    </body>
</html>
"""

user = {'nickname': 'Alessio'} # fake user
title = "Welcome to my Blog!"

# Generates the HTML text
print(Template(tpl).render(user=user, title=title))

