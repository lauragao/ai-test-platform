"""需求 ID 提取与生成规则。"""

import re


REQ_ID_PATTERNS = [
    re.compile(r"\bREQ[-_]?\d{3,}\b", re.IGNORECASE),
    re.compile(r"\bF[-_]?\d+(?:\.\d+)*\b", re.IGNORECASE),
    re.compile(r"\bUS[-_]?\d{3,}\b", re.IGNORECASE),
    re.compile(r"\b[A-Z]{2,}-\d+\b"),
    re.compile(r"需求\d+"),
]

MODULE_ABBREVIATIONS = {
    "登录": "LOGIN",
    "注册": "LOGIN",
    "用户": "USER",
    "个人中心": "USER",
    "订单": "ORDER",
    "支付": "PAY",
    "商品": "PRODUCT",
    "产品": "PRODUCT",
    "购物车": "CART",
    "搜索": "SEARCH",
    "消息": "MSG",
    "通知": "MSG",
    "设置": "CONFIG",
    "配置": "CONFIG",
}


def extract_requirement_ids(text: str) -> list[str]:
    ids: list[str] = []
    for pattern in REQ_ID_PATTERNS:
        ids.extend(match.group(0) for match in pattern.finditer(text))
    return list(dict.fromkeys(ids))


def generate_requirement_id(module: str | None, sequence: int) -> str:
    module_name = module or "REQ"
    abbreviation = MODULE_ABBREVIATIONS.get(module_name)
    if not abbreviation:
        abbreviation = re.sub(r"[^A-Za-z0-9]+", "_", module_name).strip("_").upper() or "REQ"
    return f"MOD_{abbreviation}_{sequence:03d}"
