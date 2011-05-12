from django.db import models


class Record(models.Model):
    
     proc
     status_code
     time_delta
     request_method
     path
     memory_delta
     load_delta
     queries
