from accounts.models import (
    Wallet as AccountsWallet,
    WalletTransaction as AccountsWalletTransaction,
    PlatformWallet as AccountsPlatformWallet,
    PlatformWalletTransaction as AccountsPlatformWalletTransaction,
)


class Wallet(AccountsWallet):
    class Meta:
        proxy = True
        verbose_name = 'Wallet'
        verbose_name_plural = 'Wallets'


class WalletTransaction(AccountsWalletTransaction):
    class Meta:
        proxy = True
        verbose_name = 'Wallet Transaction'
        verbose_name_plural = 'Wallet Transactions'


class PlatformWallet(AccountsPlatformWallet):
    class Meta:
        proxy = True
        verbose_name = 'Platform Wallet'
        verbose_name_plural = 'Platform Wallets'


class PlatformWalletTransaction(AccountsPlatformWalletTransaction):
    class Meta:
        proxy = True
        verbose_name = 'Platform Wallet Transaction'
        verbose_name_plural = 'Platform Wallet Transactions'
