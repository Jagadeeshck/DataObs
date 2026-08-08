from ..errors import safe_error


def validate(client, cfg):
    raw = client.invoke("subscription_get")
    sid = str(getattr(raw, "subscription_id", getattr(raw, "id", ""))).split("/")[-1].lower()
    if sid != cfg.subscription_id:
        raise safe_error("subscription_mismatch")
