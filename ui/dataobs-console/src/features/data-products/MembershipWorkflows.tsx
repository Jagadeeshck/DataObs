import { FormEvent, ReactNode, useId, useState } from "react";

type Proposal = {
  proposal_id: string;
  entity_id: string;
  state: string;
  proposal_revision: number;
};
type Membership = {
  membership_id: string;
  entity_id: string;
  state: string;
  etag: string;
};
type Decision = {
  decision_id: string;
  decision: string;
  outcome: string;
  actor: string;
  reason: string;
};
type Action = "accept" | "reject" | "expire" | "supersede";

export function MembershipList({
  items,
  onExclude,
}: {
  items: Membership[];
  onExclude: (item: Membership) => void;
}) {
  if (!items.length) return <p>No memberships are available.</p>;
  return (
    <table>
      <caption>Memberships</caption>
      <thead>
        <tr>
          <th>Entity</th>
          <th>State</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={item.membership_id}>
            <td>{item.entity_id}</td>
            <td>{item.state}</td>
            <td>
              {item.state === "active" && (
                <button type="button" onClick={() => onExclude(item)}>
                  Exclude
                </button>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function MembershipProposalList({
  items,
  onDecide,
}: {
  items: Proposal[];
  onDecide: (item: Proposal, action: Action) => void;
}) {
  if (!items.length) return <p>No membership proposals are available.</p>;
  return (
    <table>
      <caption>Membership proposals</caption>
      <thead>
        <tr>
          <th>Entity</th>
          <th>Revision</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={`${item.proposal_id}:${item.proposal_revision}`}>
            <td>{item.entity_id}</td>
            <td>{item.proposal_revision}</td>
            <td>
              {item.state === "proposed" &&
                (["accept", "reject", "expire", "supersede"] as Action[]).map(
                  (action) => (
                    <button
                      type="button"
                      key={action}
                      onClick={() => onDecide(item, action)}
                    >
                      {action[0].toUpperCase() + action.slice(1)}
                    </button>
                  ),
                )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

type DialogProps = {
  title: string;
  children?: ReactNode;
  submitting: boolean;
  onCancel: () => void;
  onSubmit: (actor: string, reason: string) => Promise<void>;
};
function DecisionDialog({
  title,
  children,
  submitting,
  onCancel,
  onSubmit,
}: DialogProps) {
  const [actor, setActor] = useState("");
  const [reason, setReason] = useState("");
  const heading = useId();
  const submit = (event: FormEvent) => {
    event.preventDefault();
    void onSubmit(actor, reason);
  };
  return (
    <div role="dialog" aria-modal="true" aria-labelledby={heading}>
      <h2 id={heading}>{title}</h2>
      {children}
      <form onSubmit={submit}>
        <label>
          Actor
          <input
            required
            maxLength={200}
            value={actor}
            onChange={(e) => setActor(e.target.value)}
          />
        </label>
        <label>
          Reason
          <textarea
            required
            maxLength={1000}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </label>
        <button type="submit" disabled={submitting}>
          {submitting ? "Submitting…" : "Confirm"}
        </button>
        <button type="button" disabled={submitting} onClick={onCancel}>
          Cancel
        </button>
      </form>
    </div>
  );
}
export const ProposalDecisionDialog = (props: DialogProps) => (
  <DecisionDialog {...props} />
);
export const MembershipExclusionDialog = (props: DialogProps) => (
  <DecisionDialog {...props} />
);

export function MembershipDecisionHistory({ items }: { items: Decision[] }) {
  return (
    <section aria-labelledby="decision-history">
      <h3 id="decision-history">Decision history</h3>
      {!items.length ? (
        <p>No decisions are available.</p>
      ) : (
        <ol>
          {items.map((item) => (
            <li key={item.decision_id}>
              {item.decision}: {item.outcome} by {item.actor} — {item.reason}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
