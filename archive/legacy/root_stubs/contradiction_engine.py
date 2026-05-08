def contradiction_score(prediction, signals):
    """
    判断预测是否被否定（冲突评分）
    score 越高 = 越危险
    """

    score = 0

    # 1. 宏观反向
    if prediction in ["大涨", "小涨"] and signals.get("macro_bearish"):
        score += 1

    # 2. 量价背离
    if prediction in ["大涨", "小涨"] and signals.get("volume_drop"):
        score += 1

    # 3. 龙头不配合
    if prediction in ["大涨", "小涨"] and signals.get("nvda_down"):
        score += 1

    # 4. 技术面过热
    if prediction in ["大涨", "小涨"] and signals.get("overbought"):
        score += 1

    return score
