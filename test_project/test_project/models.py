from django.db import models


class AdHocUserModel(models.Model):
    # pretend this email field is encrypted!
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=128, null=True, blank=True)
    last_name = models.CharField(max_length=128, null=True, blank=True)

    class Meta:
        verbose_name = "Ad hoc user"
        verbose_name_plural = "Ad hoc users"

    def __str__(self):
        return f"{self.first_name} {self.last_name} <{self.email}>"
