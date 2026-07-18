# Console deployment

Build `ui/dataobs-console/Dockerfile`. It uses a multi-stage build and unprivileged nginx runtime, immutable asset caching, SPA fallback, health endpoint, CSP, clickjacking and MIME-sniffing protection. Runtime `/api` is same-origin proxied to the API.
