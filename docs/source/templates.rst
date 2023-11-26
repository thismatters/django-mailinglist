=========
Templates
=========

This package ships with a number of default templates for formatting archived messages, admin views, and outgoing email both for mailing lists and subscription management (html and plaintext).
The default templates are sparse, but complete.
There is no need for you to provide custom templates, however you may do so if you wish.
The instructions for overriding templates is provided below.

Overriding Templates
--------------------

First and foremost ensure that your Django project is configured to locate templates in your project directory. In `settings.py` find the `TEMPLATES` variable and ensure that the `DIRS` key includes the `templates` directory for your project::

  TEMPLATES = [
    {
      ...
      "DIRS": [BASE_DIR / "my_special_project" / "templates"],
      ...
    },
  ]

or (if you're not using ``pathlib.Path`` yet)::

  TEMPLATES = [
    {
      ...
      "DIRS": [os.path.join(BASE_DIR, "my_special_project", "templates")],
      ...
    },
  ]

Now you may create templates in your project directory to override any template you wish.
Be sure that you namespace them appropriately so that they will replace the ``mailinglist`` app templates::

  my_special_project
  └── templates
    └── mailinglist  # <-- this namespace designator is needed!
      └── email
        ├── message.html
        ├── message.txt
        └── message_subject.txt

You can also override the template for a specific mailing list by creating a directory named using the mailing list ``slug``.
Supposing you had a mailing list called "Free Radicals" with a slug like ``free-radicals`` then you could override the templates for ougoing messages to that list by creating the following file structure::

  my_special_project
  └── templates
    └── mailinglist
      └── email
        └── free-radicals
          ├── message.html
          ├── message.txt
          └── message_subject.txt

And now a brief description of each default template included with the package which may be overridden::

  templates
  └── mailinglist
    ├── email
    │   ├── global-deny
    │   │   ├── subscribe.(html|txt)   : Subscription email to the global deny list
    │   │   ├── subscribe_subject.txt  : Subject for same
    │   ├── message.(html|txt)         : Outgoing mailinglist message text
    │   ├── message_subject.txt        : Subject for same
    │   ├── subscribe.(html|txt)       : Outgoing email to verify subscription
    │   ├── subscribe_subject.txt      : Subject for same
    └── web
      ├── archive
      │   ├── index.html                  : Web archive listing of messages published to a mailing list
      │   └── message.html                : Web archive of individual message published
      ├── global_unsubscribe.html         : Page for users to opt in to the global deny list
      ├── global_unsubscribe_success.html : Page for users to be told they must verify their email address
      ├── subscribe_confirm.html          : Page for users to confirm they have joined mailing list (requires subscription token to access)
      ├── subscribe.html                  : Page for users to opt in to a mailing list
      ├── subscribe_success.html          : Page for users to be told they must verify their email address
      ├── subscriptions.html              : Page for users to manage their subscriptions (requires subscription token to access)
      └── unsubscribe.html                : Page for users to confirm they have unsubscribed from a mailing list (requires subscription token to access)
