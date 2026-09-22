"""brand_lexicon.py — 品牌词→中文音译映射（MOSS 无 lexicon 支持的文本级补偿）。
应用位置：ttsd 合成前 + score_cer 参考侧归一化（两侧一致才能正确度量）。"""

LEXICON = {
    "ffmpeg": "艾夫艾姆佩格",
    "BlackHole": "布莱克厚尔",
    "blackhole": "布莱克厚尔",
    "vivo": "维沃",
    "Python": "派森",
    "python": "派森",
    "Kubernetes": "库伯内蒂斯",
    "Qwen": "千问",
    "ChatGPT": "查特吉皮提",
    "GitHub": "吉特哈布",
}

def apply(text: str) -> str:
    """按词长降序替换（避免子串先匹配）。大小写敏感键优先，再跑小写键。"""
    for k in sorted(LEXICON, key=len, reverse=True):
        if k in text:
            text = text.replace(k, LEXICON[k])
    return text
