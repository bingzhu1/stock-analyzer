def calculate_risk_score(confidence, contradiction_count, volatility):
    """
    简单风险模型（V1）

    参数：
    - confidence: 当前置信度 (0-1)
    - contradiction_count: 冲突数量
    - volatility: 波动率 (0-1)

    返回：
    - risk_score: 0-1（越高风险越大）
    """

    risk = 0

    # 1. 置信度越低，风险越高
    risk += (1 - confidence) * 0.5

    # 2. 冲突越多，风险越高
    risk += contradiction_count * 0.2

    # 3. 波动率越大，风险越高
    risk += volatility * 0.3

    return min(risk, 1)
