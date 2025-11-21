def count_vowels(s: str) -> int:
    """
    Считает количество гласных  в строке (без учёта регистра).
    """
    vowels = "aeiouаеиоуыэюя"
    return sum(1 for char in s.lower() if char in vowels)