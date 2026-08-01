# Console state and routing

`ProductContextProvider` owns authentication status, trusted tenant/environment membership, typed relative time range, global refresh generation, optional auto-refresh, identity, permissions and capability availability. Safe filters are URL-backed. Invalid range or membership values fall back to an authenticated supported value. Context switches synchronously clear the selection and cause consumers to abort and reload.

Major capability pages remain lazy where established. Registry child patterns preserve asset, pathway, stream, data-product, job, run and incident deep links. Navigation omits routes lacking a required permission; this is a UX control only and API authorization stays authoritative.
