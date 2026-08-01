import { useEffect, useState } from "react";
import { userManager } from "./oidc";

export function Login() {
  const requested = new URLSearchParams(location.search).get("next");
  const next =
    requested?.startsWith("/") && !requested.startsWith("//") ? requested : "/";
  const [error, setError] = useState(false);
  return (
    <main className="route-state">
      <h1>Sign in to DataObs</h1>
      {error && (
        <p role="alert">
          Sign in could not be started. Check the identity provider and try
          again.
        </p>
      )}
      <button
        onClick={() =>
          void userManager()
            .then((m) => m.signinRedirect({ state: { next } }))
            .catch(() => setError(true))
        }
      >
        Sign in with your identity provider
      </button>
    </main>
  );
}
export function Callback() {
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    void userManager()
      .then(async (manager) => {
        const user = await manager.signinRedirectCallback();
        history.replaceState(
          {},
          "",
          (user.state as { next?: string } | undefined)?.next?.startsWith(
            "/",
          ) && !(user.state as { next?: string }).next?.startsWith("//")
            ? (user.state as { next: string }).next
            : "/",
        );
        location.reload();
      })
      .catch(() => setFailed(true));
  }, []);
  return (
    <main className="route-state">
      {failed ? (
        <>
          <h1>Sign in was not completed</h1>
          <p role="alert">
            The identity response could not be validated. Sensitive provider
            details were withheld.
          </p>
          <a href="/login">Try again</a>
        </>
      ) : (
        <p role="status">Completing secure sign in…</p>
      )}
    </main>
  );
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
