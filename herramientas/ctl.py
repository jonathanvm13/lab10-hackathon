# Solo cuentan letras ASCII (a-z/A-Z -> 1..26) y dígitos ASCII 0-9, evaluados sobre el carácter original.
def N(m):
    out = ""
    for ch in m:
        if "a" <= ch <= "z" or "A" <= ch <= "Z": out += str(ord(ch.upper()) - 64)
        elif "0" <= ch <= "9": out += ch
    return int(out or "0")
def control(m): return 98 - (N(m) * 100) % 97
