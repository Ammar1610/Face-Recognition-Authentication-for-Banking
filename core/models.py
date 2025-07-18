from django.db import models
from userauths.models import User
from account.models import Account, DollarAccount
from shortuuid.django_fields import ShortUUIDField
# Create your models here.

TRANSACTION_TYPE = (
    ("transfer", "Transfer"),
    ("exchange", "exchange"),
    ("recieved", "Recieved"),
    ("withdraw", "withdraw"),
    ("refund", "Refund"),
    ("request", "Payment Request"),
    ("save", "Save"),
    ("none", "None"),

)

CARD_TYPE = (
    ("master", "master"),
    ("visa", "visa"),
    ("verve", "verve"),

)

TRANSACTION_STATUS = (
    ("failed", "failed"),
    ("completed", "completed"),
    ("pending", "pending"),
    ("processing", "processing"),
    ("request_sent", "request_sent"),
    ("request_settled", "request settled"),
    ("request_processing", "request processing"),

)

NOTIFICATION_TYPE = (
    ("None", "None"),
    ("Transfer", "Transfer"),
    ("Credit Alert", "Credit Alert"),
    ("Debit Alert", "Debit Alert"),
    ("Saved Funds", "Saved Funds"),
    ("Sent Payment Request", "Sent Payment Request"),
    ("Recieved Payment Request", "Recieved Payment Request"),
    ("Funded Credit Card", "Funded Credit Card"),
    ("Withdrew Credit Card Funds", "Withdrew Credit Card Funds"),
    ("Deleted Credit Card", "Deleted Credit Card"),
    ("Added Credit Card", "Added Credit Card"),

)
class Transaction(models.Model):
    transaction_id = ShortUUIDField(unique=True, length=15, max_length=20, prefix="TRN")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name = "user")
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    amount_exchange = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    amount_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)


    description = models.CharField(max_length=1000, null=True, blank=True)

    reciever= models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name = "reciever")
    sender= models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name = "sender") 

    reciever_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, related_name = "reciever_account") 
    sender_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, related_name = "sender_account") 

    sender_dollar_account = models.ForeignKey(DollarAccount, related_name="sender_dollar_transactions", null=True, blank=True, on_delete=models.CASCADE)
    reciever_dollar_account = models.ForeignKey(DollarAccount, related_name="recieved_dollar_transactions", null=True, blank=True, on_delete=models.CASCADE)

    status = models.CharField(choices=TRANSACTION_STATUS, max_length=100, default="pending")
    transaction_type = models.CharField(choices=TRANSACTION_TYPE, max_length=100, default="none")

    date = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now_add=False, null=True, blank=True)
    currency = models.CharField(max_length=10, choices=[('NGN', 'Naira'), ('USD', 'Dollar')], default='NGN')

    verification_method = models.CharField(
        max_length=10,
        choices=[('PIN', 'PIN'), ('FACE', 'Face Recognition')],
        default='PIN'
    )
    face_verification_status = models.BooleanField(default=False)  

    def __str__(self):
        try:
            return f"{self.user}"
        except:
            return f"Transaction"

    class Meta:
        indexes = [
            models.Index(fields=['user','status']),
        ]    
        
      
        

class CreditCard(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    card_id = ShortUUIDField(unique=True, length=5, max_length=20, prefix="CARD", alphabet="1234567890")

    name = models.CharField(max_length=100)
    number = models.BigIntegerField()
    month = models.IntegerField()
    year = models.IntegerField()
    cvv = models.IntegerField()

    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    card_type = models.CharField(choices=CARD_TYPE, max_length=20, default="master")
    card_status = models.BooleanField(default=True)

    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.card_id}"
    

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    notification_type = models.CharField(max_length=100, choices=NOTIFICATION_TYPE, default="none")
    amount = models.IntegerField(default=0)
    is_read = models.BooleanField(default=False)
    date = models.DateTimeField(auto_now_add=True)
    nid = ShortUUIDField(length=10, max_length=25, alphabet="abcdefghijklmnopqrstuvxyz")
    currency = models.CharField(max_length=10, choices=[('NGN', 'Naira'), ('USD', 'Dollar')], default='NGN')
    
    
    class Meta:
        ordering = ["-date"]
        verbose_name_plural = "Notification"

    def __str__(self):
        return f"{self.user} - {self.notification_type}"
    
class Recipient(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    kyc = models.ForeignKey('account.KYC', on_delete=models.CASCADE, null=True, blank=True)  # Add this line
    full_name = models.CharField(max_length=100, default=0)
    rit = ShortUUIDField(length=10, max_length=25)
    r_number = ShortUUIDField(default=0, length=10, max_length=25)
    date = models.DateTimeField(auto_now_add=True)
    account_type = models.CharField(max_length=10, choices=[('USD', 'Dollar'), ('NGN', 'Naira')], default='NGN')
    
    class Meta:
        unique_together = ('kyc', 'account_type')
    
    def __str__(self):
        return f"{self.full_name} - {self.rit}"
