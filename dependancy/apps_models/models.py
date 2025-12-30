# RateReview/models.py

from django.db import models
from django.contrib.auth.models import User

class Review(models.Model):
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    technician = models.ForeignKey('accounts.TechnicianProfile', on_delete=models.CASCADE, related_name='reviewed_technicians')
    rating = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)], default=0)  # Rating from 1 to 5
    review_text = models.TextField(blank=True, null=True)  # Optional review text
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # After saving the review, update the technician's rate field with the average rating
        reviews = Review.objects.filter(technician=self.technician)
        average_rating = reviews.aggregate(models.Avg('rating'))['rating__avg'] or 0.00
        self.technician.rate = round(average_rating, 2)  # Update the rate field in TechnicianProfile
        self.technician.save()

    def __str__(self):
        return f"Review by {self.client.username} on {self.technician.user.username} with rating {self.rating}/5"

