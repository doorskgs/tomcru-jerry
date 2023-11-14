import os
import hmac
import hashlib
import struct

from flask import request, Request, jsonify
from functools import wraps


class SecretCfg:
    def __init__(self, signature: dict, content: list[dict], *,
                 secret: str | bytes = None, file: str = None, env: str = None,
                 unauthorized: dict | str = "",
                 ):
        self.signature_getter = _getter(signature)
        self.content_getter = _getter(*content)
        self.unauthorized = unauthorized

        if secret:
            if isinstance(secret, str):
                secret = secret.encode('utf8')
            self.secret = secret
        elif file:
            with open(file, 'br') as fh:
                self.secret = fh.read().strip(b'\n')
        elif env:
            self.secret = os.environ[env].encode('utf8')
        else:
            raise NotImplementedError(f"Please configure either file, env or secret string for {secret_id}")


_secrets: dict[str, SecretCfg] = {}


def setup_secrets(cfg: dict):
    """
    Example:
        {
            "my_key": {
                "file": "my_key.bin",
                "signature": {"header": "x-hub-signature-256"},
                "content": [
                    {"header": "authorization", "sep": ";"}
                    {"sep": "--"},
                    {"header": "x-date", "sep": ";"},
                    {"body": true }
                ]
            }
        }
    """
    for secret_id, cfg in cfg.items():
        _secrets[secret_id] = SecretCfg(**cfg)


def hmac_protect(secret_cfg: SecretCfg | dict | str):
    """

    Args:
        secret_cfg:

    Examples:

    Returns:

    """
    if isinstance(secret_cfg, str):
        secret_cfg = _secrets[secret_cfg]
    elif isinstance(secret_cfg, dict):
        secret_cfg = SecretCfg(**secret_cfg)

    def actual_decorator(action):
        @wraps(action)
        def wrapper(*args, **kwargs):
            if verify_secret(secret_cfg):
                return action(*args, **kwargs)
            else:
                return jsonify(secret_cfg.unauthorized), 403

        return wrapper
    return actual_decorator


def _getter(*sources: dict):

    def browse(req: Request):
        xs: list[bytes] = []

        for source in sources:
            if source == 'body':
                xs.append(req.data)
            elif 'header' in source:
                header = req.headers[source['header']]

                if 'split' in source:
                    header = header.split(source['split'].get('sep', ' '))[source['split']['index']]

                xs.append(header.encode('utf8'))
            elif isinstance(source.get('body'), (list, tuple)):
                json_value: dict | str = req.json()
                for attr in source['body']:
                    json_value = json_value[attr]

                if isinstance(json_value, str):
                    xs.append(json_value.encode('utf8'))
                elif isinstance(json_value, int):
                    xs.append(bytes(json_value))
                elif isinstance(json_value, float):
                    xs.append(bytes(struct.pack("f", json_value)))
            if 'sep' in source:
                xs.append(source['sep'].encode('utf8'))

        return b''.join(xs)
    return browse


def verify_secret(secret_cfg: SecretCfg):
    # verify secret first
    try:
        signature: str = secret_cfg.signature_getter(request).decode('utf8')
        content: bytes = secret_cfg.content_getter(request)
        secret: bytes = secret_cfg.secret
    except (KeyError, IndexError):
        return False

    computed_sign = hmac.new(secret, content, hashlib.sha256)
    return hmac.compare_digest(computed_sign.hexdigest(), signature)


CORS_ALL = 'all'


class cors: # noqa
    def __init__(self, acl: dict):
        self.headers = {}
        self.allow = acl.get('allow', 'all')
        self.deny = acl.get('deny', [])

        if acl.get('use_defaults'):
            self.headers[
                'Access-Control-Allow-Headers'] = 'Origin, Accept, X-Requested-With, Content-Type, Authorization'
            self.headers[
                'Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            self.headers['Access-Control-Allow-Credentials'] = 'true'
            self.headers['Access-Control-Max-Age'] = 86400

        self.headers.update(acl.get('headers', {}))

        if isinstance(self.deny, list): self.deny = set(self.deny)
        if isinstance(self.allow, list): self.allow = set(self.allow)
        if '*' == self.deny: self.deny = CORS_ALL
        if '*' == self.allow: self.allow = CORS_ALL

    def __call__(self, request, resp):

        resp.headers.update(self.headers)

        if "Access-Control-Allow-Origin" not in resp.headers:
            acl_allow_origin = None

            if not request.origin:
                if self.allow == CORS_ALL and self.deny != CORS_ALL:
                    acl_allow_origin = '*'
            else:
                if self.deny != CORS_ALL and request.origin not in self.deny:
                    if self.allow == CORS_ALL or request.origin in self.allow:
                        acl_allow_origin = request.origin

            # set headers
            if acl_allow_origin:
                resp.headers["Access-Control-Allow-Origin"] = acl_allow_origin

        return resp
