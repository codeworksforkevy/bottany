PLATFORM_POLICIES = {
    # Epic: weekly free-to-keep promotions should always have an end timestamp.
    "epic": {
        "requires_claim_until": True,
        "allow_permanent_free": False,
    },

    # GOG: permanent free catalog items (no end time) + limited-time giveaways (have end time).
    "gog": {
        "requires_claim_until": False,
        "allow_permanent_free": True,
    },
    "gog_giveaway": {
        "requires_claim_until": True,
        "allow_permanent_free": False,
    },

    # Prime Gaming: downloadable games to keep forever, announced monthly on the official Prime Gaming blog.
    # We compute an end-of-month claim_until if the article doesn't provide a precise timestamp.
    "prime_gaming": {
        "requires_claim_until": True,
        "allow_permanent_free": False,
    },

    # Amazon Luna: streaming access (Included with Prime / rotating catalog). Not free-to-keep.
    "amazon_luna_streaming": {
        "requires_claim_until": False,
        "allow_permanent_free": False,
    },
}
