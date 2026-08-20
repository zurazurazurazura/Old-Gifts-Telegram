GIFTS = {
    "Christmas Teddy": 5956217000635139069,
    "Valentine Heart": 5801108895304779062,
    "Valentine Bear": 5800655655995968830,
    "Pink Teddy": 5866352046986232958,
    "Clown Teddy": 5935895822435615975,
    "Bunny Teddy": 5969796561943660080,
    "Builder Teddy": 6026193266406327981,
    "Normal Heart": 5170145012310081615,
}

def get_gift_list():
    return "\n".join(f" {name}" for name in GIFTS.keys())

def get_gift_id(gift_name):
    return GIFTS.get(gift_name)

def is_valid_gift(gift_name):
    return gift_name in GIFTS
