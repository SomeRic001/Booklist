from django.db import models



class Book(models.Model):
    ol_key = models.CharField(max_length=50, unique=True)  
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    cover_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.title


class UserBook(models.Model):
    STATUS_CHOICES = [
        ('reading', 'Reading'),
        ('completed', 'Completed'),
        ('wishlist', 'Wishlist'),
    ]

    user_id = models.IntegerField()  

    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user_id', 'book') 
    def __str__(self):
        return f"{self.user_id} - {self.book.title} ({self.status})"