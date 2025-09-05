
from .models import PasswordResetKey

import string
import random

chars = string.ascii_letters
numbs = ("1","2","3","4","5","6","7","8","9","0",)
# print(chars)
def make_password_token_and_key(length, purpose=''):
    new_token = ''
    if length <= 6:
        new_token = ''.join(str(random.randrange(10)) for x in range(length))
        if purpose == 'token':
            if PasswordResetKey.objects.filter(key=new_token).exists():
                new_token = make_password_token_and_key(length, purpose)
    else:
        # new_len = length/2
        for i in range(int(length/2)):
            new_token += random.choice(chars)
            new_token += random.choice(numbs)
        if purpose == 'reset_activation':
            if PasswordResetKey.objects.filter(token_activation_code = new_token).exists():
                new_token = make_password_token_and_key(length, purpose)
    # print(new_token)
    return(new_token)

# make_password_token_and_key(24)

def _calculate_weekly_range(date):
    start_of_week = date - timezone.timedelta(days=date.weekday())  # Monday
    end_of_week = start_of_week + timezone.timedelta(days=6)  # Sunday
    return start_of_week, end_of_week

    