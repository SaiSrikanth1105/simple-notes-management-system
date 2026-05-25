import random
def genotp():
    otp = ''
    for i in range(6):
        otp += str(random.randint(0,9))
    return otp