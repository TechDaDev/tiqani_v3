# Tiqani Models Quick Reference Guide

## Core Models Architecture

```
CustomUser (AbstractUser)
├── TechnicianProfile (OneToOne)
│   ├── TechnicianSkillSet (FK, M2M categories/skills/sub_skills)
│   └── TechnicianImage (FK)
├── ClientProfile (OneToOne)
├── AdminProfile (OneToOne)
├── DealershipProfile (OneToOne)
├── Wallet (OneToOne)
│   └── WalletTransaction (FK)
└── OTPVerification (FK)
```

---

## Model Usage Examples

### 1. Creating a Technician Profile
```python
from accounts.models import CustomUser, TechnicianProfile, TechnicianSkillSet

# Create user
user = CustomUser.objects.create_user(
    username='tech_user',
    password='secure_pass',
    email='tech@example.com',
    phone_number='07812345678',
    governorate='Baghdad',
    address='123 Street, Baghdad',
    gender='M',
    date_of_birth='1990-01-15',
    role='technician'
)

# Create profile
profile = TechnicianProfile.objects.create(
    user=user,
    job_title='HVAC Technician',
    about='Professional with 5 years experience',
    years_of_expertise=5,
    is_available=True
)

# Add skills
skillset = TechnicianSkillSet.objects.create(technician=profile)
skillset.categories.add(category_id)
```

### 2. Managing Wallet Transactions
```python
from accounts.models import Wallet, WalletTransaction
from decimal import Decimal

# Get or create wallet
wallet, created = Wallet.objects.get_or_create(user=user)

# Check balance
print(f"Balance: {wallet.balance} IQD")

# Add transaction
transaction = WalletTransaction.objects.create(
    wallet=wallet,
    transaction_type='deposit',
    amount=Decimal('50000.00'),
    amount_usd=Decimal('34.13'),  # At current exchange rate
    exchange_rate=Decimal('1465.00'),  # IQD to USD
    description='Deposit via credit card'
)

# Balance is NOT automatically updated - handle in views/tasks
```

### 3. OTP Verification Flow
```python
from accounts.models import OTPVerification

# Generate OTP
otp = OTPVerification.generate_otp(user)
print(f"OTP: {otp.otp_code}")
print(f"Verification ID: {otp.verification_id}")

# Later: Verify OTP
try:
    otp = OTPVerification.objects.get(verification_id=provided_verification_id)
    if otp.is_valid():
        if otp.otp_code == provided_code:
            otp.is_used = True
            otp.save(update_fields=['is_used'])
            # Proceed with verification
        else:
            raise ValueError("Invalid OTP code")
    else:
        raise ValueError("OTP expired")
except OTPVerification.DoesNotExist:
    raise ValueError("OTP not found")
```

### 4. Profile Completion Checking
```python
# Check if profile is complete
profile = user.technician_profile
is_complete = profile.check_profile_completion()

if not is_complete:
    incomplete_fields = profile.get_incomplete_fields()
    print("Please complete:", incomplete_fields)
    # Return to user for form validation
```

### 5. Rating System (TechnicianProfile)
```python
# Update rating after review is added
profile = user.technician_profile
profile.update_rating()

# Access cached rating
print(f"Rating: {profile.rate}/5.0")
```

---

## Field Reference

### CustomUser (Extends AbstractUser)
| Field | Type | Notes |
|-------|------|-------|
| username | CharField(150) | Unique username |
| email | EmailField | Unique email |
| phone_number | CharField(11) | Format: 07[578]XXXXXXXX |
| role | CharField | Choices: client, technician, admin, dealership |
| governorate | CharField | Iraqi governorate selection |
| address | TextField | Full address |
| gender | CharField | M/F/Other |
| date_of_birth | DateField | Calculates age property |
| profile_image | ImageField | User profile picture |
| is_delete | BooleanField | Soft delete flag |
| created_at | DateTimeField | Auto-set on creation |
| updated_at | DateTimeField | Auto-updates |

### TechnicianProfile
| Field | Type | Purpose |
|-------|------|---------|
| user | OneToOneField | Link to CustomUser |
| id | UUIDField | Primary key |
| job_title | CharField | Specialization |
| about | TextField | Bio/description |
| years_of_expertise | IntegerField | Experience years |
| is_available | BooleanField | Currently accepting jobs |
| approved | BooleanField | Admin approval |
| last_active | DateTimeField | Last activity timestamp |
| rate | DecimalField(3,2) | Cached average rating 0-5 |
| identification_documents | FileField | ID verification |
| url1, url2 | URLField | Portfolio/social links |
| is_complete | BooleanField | Profile completion flag |
| is_delete | BooleanField | Soft delete flag |

### Wallet
| Field | Type | Notes |
|-------|------|-------|
| user | OneToOneField | Unique per user |
| balance | DecimalField | IQD currency, cannot go negative |
| transaction_id | CharField(12) | Auto-generated unique ID |

### WalletTransaction
| Field | Type | Values |
|-------|------|--------|
| wallet | ForeignKey | Link to wallet |
| contract | ForeignKey | Optional link to contract |
| transaction_type | CharField | deposit, transfer_in/out, escrow, release, refund, withdrawal |
| amount | DecimalField | IQD amount |
| amount_usd | DecimalField | USD equivalent (optional) |
| exchange_rate | DecimalField | Rate at transaction time |
| description | TextField | Transaction details |
| created_at | DateTimeField | Transaction timestamp |
| updated_at | DateTimeField | Last modification |

### OTPVerification
| Field | Type | Notes |
|-------|------|-------|
| user | ForeignKey | User receiving OTP |
| otp_code | CharField(6) | 6-digit code |
| verification_id | CharField(32) | Unique tracking ID |
| created_at | DateTimeField | Generation time |
| is_used | BooleanField | Prevents reuse |

---

## Query Examples

### Get Active Technicians
```python
from accounts.models import TechnicianProfile

active_techs = TechnicianProfile.objects.filter(
    is_available=True,
    approved=True,
    is_delete=False
).select_related('user').order_by('-rate')
```

### Get Recently Updated Wallets
```python
from accounts.models import Wallet

recent_wallets = Wallet.objects.select_related('user').order_by('-updated_at')[:10]
```

### Get Pending Transactions
```python
from accounts.models import WalletTransaction

pending = WalletTransaction.objects.filter(
    transaction_type__in=['transfer_in', 'transfer_out']
).select_related('wallet__user').order_by('-created_at')
```

### Get Valid OTPs for User
```python
from accounts.models import OTPVerification
from django.utils import timezone
from datetime import timedelta

user_otps = OTPVerification.objects.filter(
    user=user,
    is_used=False,
    created_at__gte=timezone.now() - timedelta(minutes=10)
)
```

---

## Common Issues & Solutions

### Issue: ValueError when setting negative wallet balance
**Solution**: Use wallet transaction logic instead of direct balance manipulation
```python
# ❌ Wrong
wallet.balance = wallet.balance - Decimal('100')
wallet.save()

# ✅ Correct
WalletTransaction.objects.create(
    wallet=wallet,
    transaction_type='withdrawal',
    amount=Decimal('100'),
    description='User withdrawal'
)
# Then handle balance update in views/tasks
```

### Issue: OTPVerification.is_valid() returns unexpected results
**Solution**: Ensure created_at uses timezone-aware datetimes
```python
# In settings.py
USE_TZ = True

# is_valid() automatically handles timezone awareness
otp = OTPVerification.generate_otp(user)
if otp.is_valid():
    # Process OTP
```

### Issue: Profile completion shows incomplete but fields are filled
**Solution**: Check both CustomUser and Profile fields
```python
profile = user.technician_profile
incomplete = profile.get_incomplete_fields()
# Returns list including any missing CustomUser fields
```

---

## Performance Tips

### 1. Use select_related for OneToOne relationships
```python
profile = TechnicianProfile.objects.select_related('user').get(id=profile_id)
```

### 2. Use prefetch_related for reverse ForeignKey
```python
technician = TechnicianProfile.objects.prefetch_related('skill_sets', 'images').get(id=tech_id)
```

### 3. Use update_fields for targeted updates
```python
# Efficient - only updates is_complete
profile.update_completion_status()  # Uses update_fields=['is_complete']
```

### 4. Index queries by frequently filtered fields
```python
# Indexed queries (fast)
active = TechnicianProfile.objects.filter(is_available=True)
approved = TechnicianProfile.objects.filter(approved=True)
rated = TechnicianProfile.objects.filter(rate__gte=4.0)

# These have indexes defined in Meta class
```

---

## Database Indexes

### Created in Migration 0007
- `accounts_technicianimageteacher_created_...` on TechnicianImage(created_at)
- `accounts_otpv_is_used_...` on OTPVerification(is_used)
- `accounts_wallettransaction_wallet_created_...` on WalletTransaction(wallet, created_at)
- `accounts_wallettransaction_transaction_type_...` on WalletTransaction(transaction_type)
- `accounts_otpverification_user_created_...` on OTPVerification(user, created_at)

### Existing Indexes (Earlier Migrations)
- CustomUser: role, governorate
- TechnicianProfile: user, is_available+approved, approved, rate+approved, last_active, created_at
- ClientProfile: user, is_complete, is_delete
- AdminProfile: user, role, is_complete, is_delete
- DealershipProfile: user, company_registration_number, is_complete, is_delete
- Wallet: user

---

## Migration Status

**Latest Migration**: 0007_alter_technicianimage_options_and_more

**Applied Migrations**: 8 total
- 0001: Initial CustomUser & profiles
- 0002: Support models (Wallet, OTP, etc.)
- 0003: TechnicianProfile optimizations
- 0004: ClientProfile optimizations
- 0005: DealershipProfile optimizations
- 0006: AdminProfile optimizations
- 0007: Timestamps, indexes, and field enhancements

**Status**: ✅ All migrations applied successfully

---

## Next Integration Points

When implementing other apps, refer to:
- `category.Category` - Referenced in TechnicianSkillSet
- `category.Skill` - Referenced in TechnicianSkillSet
- `category.SubSkill` - Referenced in TechnicianSkillSet
- `contract.Contract` - Referenced in WalletTransaction

These use lazy string references and will auto-resolve when apps are created.

