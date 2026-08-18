from django.db import models


class Campaign(models.Model):
    name = models.CharField()
    use_shared_exp = models.BooleanField(default=True)
