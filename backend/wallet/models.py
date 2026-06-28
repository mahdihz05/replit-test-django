from django.db import models


class Wallet(models.Model):
    workspace = models.OneToOneField('workspaces.Workspace', on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'wallet_wallet'

    def __str__(self):
        return f'{self.workspace.name} - {self.balance}'


class WalletTransaction(models.Model):
    TYPE_CHOICES = [('charge', 'Charge'), ('deduct', 'Deduct')]

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'wallet_wallettransaction'
        ordering = ['-created_at']
