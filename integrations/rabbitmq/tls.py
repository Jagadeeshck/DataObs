import ssl

from .authentication import resolve_secret


def ssl_context(configuration):
    cafile = None
    if configuration.tls.ca_bundle_ref:
        ref = configuration.tls.ca_bundle_ref
        if not ref.startswith("file-ref:"):
            resolve_secret(ref)  # produces the stable invalid-reference failure
        cafile = ref[9:]
    context = ssl.create_default_context(cafile=cafile)
    context.check_hostname = configuration.tls.verify_hostname
    context.verify_mode = ssl.CERT_REQUIRED
    return context
