import hashlib
import hmac
import urllib


class VNPay:
    def __init__(self, tmn_code, hash_secret, payment_url):
        self.tmn_code = tmn_code
        self.hash_secret = hash_secret
        self.payment_url = payment_url

    def get_payment_url(self,vnp_params):
        input_data=sorted(vnp_params.items())
        query_string=urllib.parse.urlencode(input_data)

        hash_value=hmac.new(self.hash_secret.encode(),
                            query_string.encode(),hashlib.sha512).hexdigest()
        return f"{self.payment_url}?{query_string}&vnp_SecureHash={hash_value}"

    def validate_response(self,response_data):
        vnp_secure_hash=response_data.get('vnp_SecureHash')
        data = response_data.copy()
        data.pop('vnp_SecureHash', None)
        data.pop('vnp_SecureHashType', None)
        input_data = sorted(data.items())
        query_string = urllib.parse.urlencode(input_data)
        hash_value=hmac.new(self.hash_secret.encode(),
                            query_string.encode(),hashlib.sha512).hexdigest()
        return vnp_secure_hash==hash_value






