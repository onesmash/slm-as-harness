"""text_pipeline.py — 文本预处理与设备发现的单一共享模块。

ttsd.py / speak.py / score_cer.py / selftest.py 统一从这里导入，
保证合成侧与评分侧的归一化逻辑**逐字符一致**（CER 有效性的前提）。

组件:
  - LEXICON / apply_lexicon: 品牌词→中文音译（再导出自 brand_lexicon）
  - normalize_numbers: 数字→中文读法 v3（千分位逗号 + cn2an；先过品牌词映射）
  - find_device / find_bh_input: 按名称子串匹配输出/输入设备
"""
import re

try:
    from brand_lexicon import LEXICON, apply as apply_lexicon
except ImportError:  # 独立使用时的降级
    LEXICON, apply_lexicon = {}, lambda t: t

try:
    import cn2an
except ImportError:
    cn2an = None

_NUM_COMMA = re.compile(r"(\d),(\d{3})(?!\d)")   # 仅作历史留档：旧实现单次替换，已由下方 v4 取代
# v4 修复（cross-sentence-consistency 研究 [146]）：旧写法只做**一次** re.sub，于是
# 「1,234,567」被剥成「一千二百三十四,五百六十七」——残留 ASCII 逗号与全角「，」编码为
# 同一个 token（5448），字面上就是一个韵律停顿 token，把一笔金额读成两个数字；
# 实测期望的单个数字串出现率 0/24，且坏臂内部停顿 340–1200 ms（中位 590 ms）。
# 修法：反复剥掉「数字,数字」之间的分隔符直到收敛（右边界用 lookahead，故 groups 可重叠）。
_NUM_COMMA_ANY = re.compile(r"(?<=\d),(?=\d)")


def strip_thousand_separators(text: str) -> str:
    """剥掉**所有**数字之间的千分位逗号（多组分组也剥净），返回收敛后的文本。

    只匹配「左右都是数字」的逗号，所以中文并列里的逗号（如「一,二」）不受影响。
    """
    prev = None
    while prev != text:
        prev = text
        text = _NUM_COMMA_ANY.sub("", text)
    return text


def normalize_numbers(text: str) -> str:
    """数字→中文读法 v4（品牌词映射 → 千分位逗号修复 → cn2an 转换）。"""
    try:
        text = apply_lexicon(text)
    except Exception:
        pass
    text = strip_thousand_separators(text)
    if cn2an:
        try:
            return cn2an.transform(text, "an2cn")
        except Exception:
            pass
    return text


def find_device(name_hint: str, min_out: int = 0, min_in: int = 0):
    """按名称子串匹配输出设备；返回 (索引|None, 设备名列表)。"""
    import sounddevice as sd
    hit, names = None, []
    for i in range(len(sd.query_devices())):
        d = sd.query_devices(i)
        names.append(d["name"])
        if (name_hint.lower() in d["name"].lower()
                and d["max_output_channels"] >= min_out
                and d["max_input_channels"] >= min_in):
            hit = i
            break
    return hit, names


def find_bh_output():
    out, _ = find_device("blackhole", min_out=2)
    return out


def find_bh_input():
    inp, _ = find_device("blackhole", min_in=2)
    return inp
