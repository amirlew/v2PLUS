from telegram import LabeledPrice


def create_stars_payload(user_id, product_id):
    return f"vitoplus:stars:{int(user_id)}:{int(product_id)}"


def create_stars_invoice(title, description, payload, stars_amount):
    if isinstance(stars_amount, bool):
        raise ValueError("Stars amount must be a positive integer.")

    try:
        stars_amount = int(stars_amount)
    except (TypeError, ValueError):
        raise ValueError("Stars amount must be a positive integer.")

    if stars_amount <= 0:
        raise ValueError("Stars amount must be positive.")

    if not payload:
        raise ValueError("Invoice payload is required.")

    title = str(title).strip()
    description = str(description).strip()
    payload = str(payload)

    if not title:
        raise ValueError("Invoice title is required.")

    if not description:
        raise ValueError("Invoice description is required.")

    return {
        "title": title[:32],
        "description": description[:255],
        "payload": payload,
        "provider_token": "",
        "currency": "XTR",
        "prices": [
            LabeledPrice(
                label=title[:32],
                amount=stars_amount
            )
        ],
    }


def is_valid_stars_payment(
    payment,
    expected_payload=None,
    expected_amount=None
):
    if payment is None:
        return False

    if getattr(payment, "currency", None) != "XTR":
        return False

    total_amount = getattr(payment, "total_amount", None)

    if (
        not isinstance(total_amount, int)
        or isinstance(total_amount, bool)
        or total_amount <= 0
    ):
        return False

    charge_id = getattr(
        payment,
        "telegram_payment_charge_id",
        None
    )

    if not charge_id:
        return False

    if expected_amount is not None:
        try:
            expected_amount = int(expected_amount)
        except (TypeError, ValueError):
            return False

        if expected_amount <= 0:
            return False

        if total_amount != expected_amount:
            return False

    if expected_payload is not None:
        if getattr(payment, "invoice_payload", None) != expected_payload:
            return False

    return True


def is_valid_pre_checkout(
    query,
    expected_payload,
    expected_amount
):
    if query is None:
        return False

    try:
        expected_amount = int(expected_amount)
    except (TypeError, ValueError):
        return False

    if expected_amount <= 0:
        return False

    return (
        getattr(query, "currency", None) == "XTR"
        and getattr(query, "invoice_payload", None) == expected_payload
        and getattr(query, "total_amount", None) == expected_amount
    )


def get_payment_charge_id(payment):
    if not is_valid_stars_payment(payment):
        return None

    return payment.telegram_payment_charge_id