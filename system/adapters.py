from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
import pprint

class NoUsernameAccountAdapter(DefaultAccountAdapter):
    def populate_username(self, request, user):
        # Skip setting username entirely
        return

class NoUsernameSocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)

        # DEBUG: Print the extra_data dictionary from Google
        print("\n--- GOOGLE LOGIN EXTRA DATA ---")
        pprint.pprint(sociallogin.account.extra_data)
        print("--- END EXTRA DATA ---\n")

        # Ensure username is never set
        if hasattr(user, 'username'):
            user.username = None

        # Pull data directly from Google's extra_data
        extra_data = sociallogin.account.extra_data
        given_name = extra_data.get('given_name', '')
        family_name = extra_data.get('family_name', '')
        full_name = extra_data.get('name') or f"{given_name} {family_name}".strip()

        if hasattr(user, 'full_name') and not user.full_name:
            user.full_name = full_name

        # Google usually won't return phone_number
        if hasattr(user, 'phone_number') and not user.phone_number:
            user.phone_number = ""

        # Set your custom flags here
        if hasattr(user, 'email_verified'):
            user.email_verified = True
        if hasattr(user, 'account_status'):
            user.account_status = 'active'  # or the exact value you use for active
        if hasattr(user, 'is_active'):
            user.is_active = True

        return user
