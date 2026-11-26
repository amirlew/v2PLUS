def is_valid_integer(value):
    try:
        int(value)
        return True
    except (ValueError, TypeError):
        return False


def is_positive_integer(value):
    try:
        return int(value) > 0
    except (ValueError, TypeError):
        return False


def is_valid_volume(value, maximum=100):
    try:
        volume = int(value)
        return 0 < volume <= maximum
    except (ValueError, TypeError):
        return False


def is_valid_price(value):
    try:
        return int(value) >= 0
    except (ValueError, TypeError):
        return False


def calculate_custom_price(volume):
    volume = int(volume)

    if volume <= 0 or volume > 100:
        raise ValueError("Invalid volume")

    if volume <= 30:
        return volume * 3000

    return (30 * 3000) + ((volume - 30) * 2000)