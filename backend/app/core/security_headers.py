_HEADERS = [
    (b'x-content-type-options', b'nosniff'),
    (b'x-frame-options', b'DENY'),
    (b'referrer-policy', b'strict-origin-when-cross-origin'),
    (b'strict-transport-security', b'max-age=63072000; includeSubDomains'),
    (b'permissions-policy', b'geolocation=(), payment=(), usb=()'),
]


class SecurityHeadersMiddleware:
    """Adds baseline HTTP security headers without buffering streaming responses."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            if message['type'] == 'http.response.start':
                hdrs = list(message.get('headers', []))
                present = {k.lower() for k, _ in hdrs}
                for k, v in _HEADERS:
                    if k not in present:
                        hdrs.append((k, v))
                message = {**message, 'headers': hdrs}
            await send(message)

        await self.app(scope, receive, send_wrapper)
