import random
def genotp():
    u_l = [chr(i) for i in range(ord('A'),ord('Z')+1)]
    s_l = [chr(i) for i in range(ord('a'),ord('z')+1)]
    otp = ''
    for i in range(2):
        otp = otp+random.choice(u_l)
        otp = otp+random.choice(s_l)
        otp = otp+str(random.randint(0,9))
    return otp
