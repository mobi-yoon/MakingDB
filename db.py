import json
import math
from pathlib import Path

RECIPES_PATH = Path(__file__).parent / "data" / "recipes.json"
SCROLLS_PATH = Path(__file__).parent / "data" / "scrolls.json"
MATERIALS_PATH = Path(__file__).parent / "data" / "materials.json"


def _atomic_write_json(path, data):
    """저장 도중 에러가 나도 원본 파일이 잘리지 않도록, 임시 파일에 다 쓴 뒤 교체."""
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp_path.replace(path)


# ---------- 제작법 ----------

def load_recipes(path=RECIPES_PATH):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_recipes(recipes, path=RECIPES_PATH):
    _atomic_write_json(path, recipes)


def build_indexes(recipes):
    by_name = {r["name"]: r for r in recipes}

    by_material = {}
    for r in recipes:
        for mat in r["materials"]:
            by_material.setdefault(mat["name"], []).append(
                {"name": r["name"], "qty": mat["qty"]}
            )

    return by_name, by_material


def recipe_exists(by_name, name):
    return name in by_name


def get_major_category(by_name, name):
    """제작법이 없으면 재료템(None), 있으면 major_category('가공품'/'제작품')를 반환."""
    recipe = by_name.get(name)
    return recipe["major_category"] if recipe else None


def add_recipe(recipes, by_name, major_category, sub_category, name, output_qty, materials):
    if recipe_exists(by_name, name):
        raise ValueError(f"이미 존재하는 완제품 이름입니다: {name}")

    recipe = {
        "major_category": major_category,
        "sub_category": sub_category,
        "name": name,
        "output_qty": output_qty,
        "materials": materials,
    }
    recipes.append(recipe)
    by_name[name] = recipe

    return recipe


def find_by_product(by_name, name):
    return by_name.get(name)


def remove_recipe(recipes, by_name, name):
    recipe = by_name.pop(name, None)
    if recipe is not None:
        recipes.remove(recipe)
    return recipe


def update_recipe(recipe, major_category, sub_category, output_qty, materials):
    recipe["major_category"] = major_category
    recipe["sub_category"] = sub_category
    recipe["output_qty"] = output_qty
    recipe["materials"] = materials
    return recipe


def find_products_using_material(by_material, material_name):
    return by_material.get(material_name, [])


def breakdown_tree(by_name, name, qty=1, visited=None):
    if visited is None:
        visited = frozenset()

    if name in visited:
        raise ValueError(f"순환 참조가 감지되었습니다: {name}")

    recipe = by_name.get(name)
    if recipe is None:
        return {"name": name, "qty": qty, "is_raw": True, "children": [],
                "crafts": None, "produced": qty}

    output_qty = recipe.get("output_qty", 1)
    crafts = math.ceil(qty / output_qty)
    produced = crafts * output_qty

    next_visited = visited | {name}
    children = [
        breakdown_tree(by_name, mat["name"], mat["qty"] * crafts, next_visited)
        for mat in recipe["materials"]
    ]
    return {"name": name, "qty": qty, "is_raw": False, "children": children,
             "crafts": crafts, "produced": produced}


def summarize_requirements(tree):
    """분해 트리(루트=완제품 자신 제외)를 가공품 집계와 원재료 집계로 나눠 반환."""
    processed = {}
    raw = {}

    def walk(node, is_root):
        if not is_root:
            if node["is_raw"]:
                raw[node["name"]] = raw.get(node["name"], 0) + node["qty"]
            else:
                entry = processed.setdefault(node["name"], {"qty": 0, "crafts": 0, "produced": 0})
                entry["qty"] += node["qty"]
                entry["crafts"] += node["crafts"]
                entry["produced"] += node["produced"]

        for child in node["children"]:
            walk(child, False)

    walk(tree, True)
    return processed, raw


# ---------- 원재료 ----------

def load_materials(path=MATERIALS_PATH):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_materials(materials, path=MATERIALS_PATH):
    _atomic_write_json(path, materials)


def material_exists(materials, name):
    return name in materials


def is_known_name(by_name, materials, name):
    """이름이 제작법(가공품/제작품)이나 등록된 원재료 중 하나로 이미 존재하는지."""
    return name in by_name or name in materials


def add_material(materials, name):
    if material_exists(materials, name):
        raise ValueError(f"이미 등록된 원재료입니다: {name}")
    materials.append(name)
    return name


def remove_material(materials, name):
    if name in materials:
        materials.remove(name)
        return name
    return None


# ---------- 스크롤 ----------

def load_scrolls(path=SCROLLS_PATH):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_scrolls(scrolls, path=SCROLLS_PATH):
    _atomic_write_json(path, scrolls)


def scroll_exists(scrolls, scroll_type, target_name):
    return any(
        s["scroll_type"] == scroll_type and s["target_name"] == target_name
        for s in scrolls
    )


def find_scroll(scrolls, scroll_type, target_name):
    for s in scrolls:
        if s["scroll_type"] == scroll_type and s["target_name"] == target_name:
            return s
    return None


def validate_scroll_target(by_name, scroll_type, target_name):
    """스크롤 종류에 맞는 대상인지 검증. (통과여부, 실패사유) 튜플 반환."""
    major = get_major_category(by_name, target_name)

    if scroll_type in ("채집", "채광"):
        if major is not None:
            return False, (
                f"'{target_name}'은(는) 이미 제작법이 있는 항목({major})이라 "
                f"{scroll_type} 스크롤 대상이 될 수 없습니다."
            )
        return True, None

    if scroll_type in ("제작", "요리"):
        if major != "제작품":
            reason = "제작법이 없는 재료템" if major is None else f"'{major}'로 분류된 항목"
            return False, f"'{target_name}'은(는) {reason}이라 {scroll_type} 스크롤 대상이 될 수 없습니다."
        return True, None

    # 그 외 스크롤 종류는 별도 제약 없음
    return True, None


def add_scroll(scrolls, scroll_type, town, target_name, qty_per_scroll):
    scroll = {
        "scroll_type": scroll_type,
        "town": town,
        "target_name": target_name,
        "qty_per_scroll": qty_per_scroll,
    }
    scrolls.append(scroll)
    return scroll


def remove_scroll(scrolls, scroll_type, target_name):
    scroll = find_scroll(scrolls, scroll_type, target_name)
    if scroll is not None:
        scrolls.remove(scroll)
    return scroll


def update_scroll(scroll, town, qty_per_scroll):
    scroll["town"] = town
    scroll["qty_per_scroll"] = qty_per_scroll
    return scroll
