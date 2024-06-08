from django.db import models

# Create your models here.

from django_random_id_model import RandomIDModel
import random
import string
from django.conf import settings
from django.db import models

class RandomIDModel(models.Model):
    id = models.BigAutoField(primary_key=True, max_length=settings.ID_DIGITS_LENGTH, unique=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = self.generate_unique_id()
        super(RandomIDModel, self).save(*args, **kwargs)

    def generate_unique_id(self):
        alphabet = string.digits
        while True:
            unique_id = ''.join(random.choice(alphabet) for _ in range(settings.ID_DIGITS_LENGTH))
            if not self.__class__.objects.filter(id=unique_id).exists():
                return unique_id
            
class user_details(RandomIDModel):    
    name=models.CharField(max_length=250,null=True)
    useremail=models.CharField(max_length=250)
    country=models.CharField(max_length=20)
    password=models.CharField( max_length=250,null=True)
    date_created=models.DateTimeField(auto_now_add=True,null=True)
    