#!/usr/bin/env python

from Crypto import Random
from Crypto.Cipher import AES

import base64

# cipher helpers
_AES_BS_ = 32
_PAD_CH_ = '='

_pad_ = lambda s: s + (_AES_BS_ - len(s) % _AES_BS_) * _PAD_CH_

# encode value
def encrypt(key, val):
    return base64.b64encode(AES.new(key).encrypt(_pad_(val)))

# decode value
def decrypt(key, val):
    return AES.new(key).decrypt(base64.b64decode(val)).rstrip(_PAD_CH_)
