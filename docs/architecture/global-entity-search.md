# Global entity search

Team 5 owns an explicit provider registry and a generation-based controller. Queries of at least two characters are debounced for 250 ms. Each provider returns at most five mapped results; the controller runs at most ten providers, returns at most 25 deduplicated results, times each provider out at 1.5 seconds, and stops globally at two seconds. Tenant/environment changes and dialog closure abort work, and generation checks reject late responses. Partial failures remain usable.
