from platform_policies import PLATFORM_POLICIES

def classify_games(entries):
    free_to_keep = []
    discounted = []
    rejected = []

    for g in entries:
        platform = g.get("platform")
        policy = PLATFORM_POLICIES.get(platform, {})

        price = g.get("price")
        is_free = g.get("free_to_keep", False)
        claim_until = g.get("claim_until")

        # Enforce platform policy
        if policy.get("requires_claim_until") and not claim_until:
            rejected.append(g)
            continue

        if price == 0 and is_free:
            free_to_keep.append(g)
        else:
            discounted.append(g)

    return free_to_keep, discounted, rejected
