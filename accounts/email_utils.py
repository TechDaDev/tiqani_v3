"""Email utilities for sending notifications to users."""

from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string


def send_otp_email(user, otp_code, verification_id):
    """
    Send OTP verification email to user.
    
    Args:
        user: CustomUser instance
        otp_code: 6-digit OTP code
        verification_id: Unique verification identifier
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        subject = 'Email Verification Code - Tiqani'
        context = {
            'user_name': user.get_full_name() or user.username,
            'otp_code': otp_code,
            'validity_minutes': settings.OTP_VALIDITY_SECONDS // 60,
        }
        
        # Try to render HTML template if available, fallback to plain text
        try:
            html_message = render_to_string('accounts/emails/otp_verification.html', context)
        except:
            html_message = None
        
        plain_message = f"""
Hello {context['user_name']},

Your email verification code is:

{otp_code}

This code will expire in {context['validity_minutes']} minutes.

If you did not request this code, please ignore this email.

---
Tiqani Team
"""
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending OTP email: {str(e)}")
        return False


def send_welcome_email(user):
    """
    Send welcome email to newly registered user.
    
    Args:
        user: CustomUser instance
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        subject = 'Welcome to Tiqani!'
        context = {
            'user_name': user.get_full_name() or user.username,
            'user_role': user.get_role_display(),
        }
        
        try:
            html_message = render_to_string('accounts/emails/welcome.html', context)
        except:
            html_message = None
        
        plain_message = f"""
Hello {context['user_name']},

Welcome to Tiqani! Your account has been successfully created.

Role: {context['user_role']}

You can now log in and start using the platform.

---
Tiqani Team
"""
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending welcome email: {str(e)}")
        return False


def send_password_reset_email(user, otp_code):
    """
    Send password reset email with OTP code to user.
    
    Args:
        user: CustomUser instance
        otp_code: 6-digit OTP code
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        subject = 'Password Reset Code - Tiqani'
        context = {
            'user_name': user.get_full_name() or user.username,
            'otp_code': otp_code,
            'validity_minutes': settings.OTP_VALIDITY_SECONDS // 60,
        }
        
        try:
            html_message = render_to_string('accounts/emails/password_reset.html', context)
        except:
            html_message = None
        
        plain_message = f"""
Hello {context['user_name']},

You requested a password reset for your Tiqani account.

Your password reset code is:

{otp_code}

This code will expire in {context['validity_minutes']} minutes.

If you did not request this, please ignore this email and your password will remain unchanged.

---
Tiqani Team
"""
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending password reset email: {str(e)}")
        return False
