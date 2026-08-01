import { useEffect } from "react";
import { userManager } from "./oidc";

export function Login() {
  const requested = new URLSearchParams(location.search).get("next") || "/";
  const next = requested.startsWith("/") && !requested.startsWith("//") ? requested : "/";
  return (
    <button
      onClick={() =>
        void userManager().then((m) => m.signinRedirect({ state: { next } }))
      }
    >
      Sign in with your identity provider
    </button>
  );
}
export function Callback() {
  useEffect(() => {
    void userManager().then(async (manager) => {
      const user = await manager.signinRedirectCallback();
      const requested = (user.state as { next?: string } | undefined)?.next || "/";
      history.replaceState({}, "", requested.startsWith("/") && !requested.startsWith("//") ? requested : "/");
      location.reload();
    });
  }, []);
  return <p role="status">Completing secure sign in…</p>;
}
export function Logout() {
  useEffect(() => {
    void userManager().then(async (manager) => {
      await manager.removeUser();
      await manager.signoutRedirect();
    });
  }, []);
  return <p role="status">Signing out…</p>;
}
export function Unauthorised() {
  return (
    <main>
      <h1>Access denied</h1>
      <p>Your authenticated identity does not have the required permission.</p>
    </main>
  );
}
