=====
Usage
=====

#) Start development server in your typical way.
#) Navigate to ``/admin/`` and observe the "Mailinglist" section.
#) Click into "Mailing lists" and create a mailing list.
#) Click into "Subscriptions" and create a subscription for yourself.
#) Click into "Messages" and create a message (comprised of several "Message parts") and attach files as you like.
#) After saving the message, preview the message (from the link in the list view or edit view) and click the "Create Submission" button.
#) Click the "Publish" button to mark the submission for sending.
#) Run ``python manage.py process_submissions`` to actually send messages.

See the :ref:`reference` for more information on the models.

Autosending
-----------

A shared (Celery) task is provided for ``celery`` (and ``django-celery-beat``) users which can be set up as a recurring task, look for ``mailinglist.tasks.process_submissions``.

Alternately, you can set up a cronjob to periodically run the ``process_submissions`` management command.

User Signup Form
----------------

Users can sign up for mailing lists by visiting the subscription url: ``/mailinglist/subscribe/<mailing_list_slug>/``. There they will find a form for signing up for the mailing list named in the URL. It is also possible to include a signup form on any page you wish by including the following in your template::

    <form action="{% url 'mailinglist:subscribe' '<mailing_list_slug>' %}" method="post">
        {% csrf_token %}
        <label for="id_email">E-mail:</label> <input type="email" name="email" required="" id="id_email">
        <label for="id_first_name">First Name:</label> <input type="text" name="first_name" required="" id="id_first_name">
        <label for="id_last_name">Last Name:</label> <input type="text" name="last_name" required="" id="id_last_name">
        <input type="submit" value="Submit">
    </form>
