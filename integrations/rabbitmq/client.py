from __future__ import annotations

import json
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from .errors import RabbitMqError, error
from .pagination import decode_page
from .tls import ssl_context


class _ConfinedRedirects(HTTPRedirectHandler):
    def __init__(self, authority):
        self.authority = authority

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urlsplit(newurl)
        if (target.scheme, target.hostname, target.port) != self.authority:
            raise error("management_api_unavailable", "redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class RabbitMqManagementClient:
    """A deliberately non-generic, GET/HEAD-only Management HTTP API client."""

    def __init__(self, configuration, opener=None):
        self.configuration = configuration
        endpoint = urlsplit(configuration.endpoint)
        authority = (endpoint.scheme, endpoint.hostname, endpoint.port)
        self._opener = opener or build_opener(
            HTTPSHandler(context=ssl_context(configuration)), _ConfinedRedirects(authority)
        )

    def _read(self, path, *, query=None, head=False):
        url = urljoin(self.configuration.endpoint + "/", path.lstrip("/"))
        if query:
            url += "?" + urlencode(query)
        request = Request(
            url,
            method="HEAD" if head else "GET",
            headers={
                "Authorization": self.configuration.authentication.authorization_header(),
                "Accept": "application/json",
                "User-Agent": "DataObs-RabbitMQ-Collector/1",
            },
        )
        try:
            response = self._opener.open(request, timeout=self.configuration.limits["request_timeout_seconds"])
            if head:
                return {}
            maximum = self.configuration.limits["maximum_response_bytes"]
            body = response.read(maximum + 1)
            if len(body) > maximum:
                raise error("response_too_large", path.split("/")[2] if "/" in path else "management")
            return json.loads(body)
        except RabbitMqError:
            raise
        except HTTPError as exc:
            code = (
                "authentication_failed"
                if exc.code == 401
                else "access_denied" if exc.code == 403 else "management_api_unavailable"
            )
            raise error(code, path, exc.code >= 500, f"{exc.code // 100}xx") from None
        except (TimeoutError, socket.timeout):
            raise error("request_timeout", path, True) from None
        except (URLError, OSError, ValueError, json.JSONDecodeError):
            raise error("connection_failed", path, True) from None

    def overview(self):
        return self._read("/api/overview")

    def service_health(self):
        return self._read("/api/health/checks/is-in-service")

    def alarm_health(self):
        return self._read("/api/health/checks/alarms")

    def paginated(self, path):
        limits = self.configuration.limits
        for number in range(1, limits["maximum_pages"] + 1):
            payload = self._read(path, query={"page": number, "page_size": limits["page_size"], "pagination": "true"})
            page = decode_page(payload, number)
            yield from page.items
            if number >= page.page_count:
                return
        raise error("pagination_limit_reached", path)
