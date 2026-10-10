"""Unit tests for scratchpad analyzer and reasoning token accounting."""

from rewardgate.scratchpad import ScratchpadAnalyzer


def test_scratchpad_reasoning_tokens_detected():
    analyzer = ScratchpadAnalyzer(exempt_scratchpad=True)

    code_with_scratchpad = '''
# Step 1: We need to compute greatest common divisor using Euclidean algorithm.
# Invariant: gcd(a, b) = gcd(b, a % b)
# Reason: Base case is when b becomes zero, then a is the gcd.
def gcd(a: int, b: int) -> int:
    while b != 0:
        a, b = b, a % b
    return a
'''
    analysis = analyzer.analyze(code_with_scratchpad)

    assert analysis.is_scratchpad_load_bearing is True
    assert analysis.scratchpad_tokens > 20
    assert analysis.executable_lines == 4
    assert "gcd(a, b) = gcd(b, a % b)" not in analysis.clean_code
    assert "def gcd(a: int, b: int) -> int:" in analysis.clean_code


def test_scratchpad_exemption_protects_bloat_factor():
    exempt_analyzer = ScratchpadAnalyzer(exempt_scratchpad=True)
    penalizing_analyzer = ScratchpadAnalyzer(exempt_scratchpad=False)

    code_with_massive_reasoning = '''
# Thinking process:
# Step 1: check if target in array
# Step 2: use binary search for O(log n) complexity
# Step 3: initialize low and high pointers
# Step 4: calculate mid safely against overflow
# Step 5: narrow search space until low exceeds high
def binary_search(arr, target):
    low, high = 0, len(arr) - 1
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1
'''
    res_exempt = exempt_analyzer.analyze(code_with_massive_reasoning)
    res_penalizing = penalizing_analyzer.analyze(code_with_massive_reasoning)

    # When exempt, bloat factor is lower because reasoning tokens aren't counted against code bloat
    assert res_exempt.bloat_factor <= res_penalizing.bloat_factor
    assert res_exempt.is_scratchpad_load_bearing is True


def test_empty_code_handling():
    analyzer = ScratchpadAnalyzer()
    res = analyzer.analyze("")
    assert res.total_tokens == 0
    assert res.scratchpad_tokens == 0
    assert res.is_scratchpad_load_bearing is False
    assert res.clean_code == ""
