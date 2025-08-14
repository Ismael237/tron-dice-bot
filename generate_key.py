import os
import base64

def generate_key():
    key = os.urandom(32)
    print('Your 32-byte encryption key (base64):')
    print(base64.b64encode(key).decode())

if __name__ == '__main__':
    generate_key() 