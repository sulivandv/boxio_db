from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN

SINGULAR_UNITS = {"un", "cx", "pc", "kit"}
FRACTIONAL_UNITS = {"ml", "l", "g", "kg", "lb", "mm", "cm", "in"}

def normalize_code(code: str) -> str:
    return (code or "").strip().lower()

def is_fractional(code: str, units: list[dict]) -> bool:
    code = normalize_code(code)
    for unit in units:
        if unit.get("codigo") == code:
            return bool(unit.get("fracionavel"))
    return code in FRACTIONAL_UNITS

def get_unit(code: str, units: list[dict]) -> dict:
    code = normalize_code(code)
    for unit in units:
        if unit.get("codigo") == code:
            return unit
    raise ValueError(f"Unidade de medida não cadastrada: {code}")

def round_value(value: float, precision: int = 2, mode: str = "half_up") -> float:
    rounding = ROUND_HALF_UP if mode == "half_up" else ROUND_HALF_EVEN
    quant = Decimal("1") if precision <= 0 else Decimal("1").scaleb(-precision)
    return float(Decimal(str(value)).quantize(quant, rounding=rounding))

def convert_value(value: float, from_code: str, to_code: str, units: list[dict], rounding: str = "half_up") -> float:
    from_u = get_unit(from_code, units)
    to_u = get_unit(to_code, units)
    if from_u.get("dimensao") != to_u.get("dimensao"):
        raise ValueError("Não é possível converter unidades de dimensões diferentes.")
    base_value = float(value) * float(from_u.get("fator_para_base", 1))
    result = base_value / float(to_u.get("fator_para_base", 1))
    return round_value(result, int(to_u.get("precisao_decimal", 2)), rounding)

def physical_total(estoque_atual: float, quantidade_base: float, unidade: str, units: list[dict]) -> float:
    if is_fractional(unidade, units):
        return float(estoque_atual) * float(quantidade_base)
    return float(estoque_atual)
