import { useEffect } from "react";
import { userManager } from "./oidc";

export function Login() {
  const next = new URLSearchParams(location.search).get("next") || "/";
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
      history.replaceState(
        {},
        "",
        (user.state as { next?: string } | undefined)?.next || "/",
      );
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
