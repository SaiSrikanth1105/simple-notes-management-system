from itsdangerous import URLSafeTimedSerializer
from keys import secret_key,salt
def endata(data):
    serializer=URLSafeTimedSerializer(secret_key)
    return serializer.dumps(data, salt='codegnan@2017')
def dndata(data):
    serializer=URLSafeTimedSerializer(secret_key)
    return serializer.loads(data,salt='codegnan@2017')