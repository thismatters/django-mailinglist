# Generated by Django 4.2.7 on 2023-12-03 14:41

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("mailinglist", "0002_messageattachment"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="messagepart",
            options={"ordering": ["order"]},
        ),
    ]
