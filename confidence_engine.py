def evaluate_confidence(
    base_confidence,
    top1_margin,
    is_tail,
    has_conflict
):
    """
    置信系统 v1
    """

    confidence = base_confidence

    # 1. tail 限制
    if is_tail:
        confidence = "medium"

    # 2. 极端 margin 降级
    if top1_margin >= 0.60:
        confidence = "medium"

    # 3. high 条件限制
    if confidence == "high":
        if not (
            base_confidence == "high"
            and not is_tail
            and 0.10 <= top1_margin <= 0.40
            and not has_conflict
        ):
            confidence = "medium"

    return confidence
