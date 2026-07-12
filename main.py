import sys

# LANG=C.UTF-8 환경에서는 encoding이 이미 "utf-8"이어도 errors가
# "surrogateescape"로 설정돼 깨진 입력이 조용히 넘어갔다가 저장 시점에
# 터진다. errors까지 명시적으로 맞춰야 입력 시점에 바로 에러가 난다.
sys.stdout.reconfigure(encoding="utf-8", errors="strict")
sys.stdin.reconfigure(encoding="utf-8", errors="strict")

import db

MAJOR_CATEGORIES = ["가공품", "제작품"]
DEFAULT_SCROLL_TYPES = ["채집", "채광", "제작", "요리"]


def confirm_yes_no(prompt, allow_quit=False):
    """y/n을 받는다. 애매한 입력(오타 등)이면 취소로 넘기지 않고 다시 물어본다."""
    while True:
        answer = input(prompt).strip().lower()
        if allow_quit and answer == "q":
            return "q"
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no", ""):
            return False
        print("  y 또는 n으로 답해주세요.")


def input_materials(by_name, known_materials):
    materials = []
    print("재료를 입력하세요. 재료 이름을 빈 값으로 입력하면 종료합니다. (q: 메인 메뉴로 취소)")
    while True:
        name = input("  재료 이름: ").strip()
        if name.lower() == "q":
            return None
        if not name:
            break

        if not db.is_known_name(by_name, known_materials, name):
            confirm = confirm_yes_no(
                f"  '{name}'은(는) 처음 보는 이름입니다. 새 원재료로 등록하고 계속할까요? (y/N): "
            )
            if not confirm:
                print("  다시 입력해주세요.")
                continue
            db.add_material(known_materials, name)
            db.save_materials(known_materials)
            print(f"  '{name}' 원재료로 등록했습니다.")

        qty_raw = input(f"  {name} 수량: ").strip()
        if qty_raw.lower() == "q":
            return None
        try:
            qty = int(qty_raw)
        except ValueError:
            print("  수량은 숫자로 입력해주세요. 다시 입력합니다.")
            continue
        materials.append({"name": name, "qty": qty})
    return materials


def cmd_add(recipes, by_name, materials_db):
    while True:
        print("대분류:")
        for i, m in enumerate(MAJOR_CATEGORIES, 1):
            print(f"  {i}. {m}")

        major_input = input("대분류 (번호 선택, q: 메인 메뉴로): ").strip()
        if major_input.lower() == "q":
            break

        if major_input.isdigit() and 1 <= int(major_input) <= len(MAJOR_CATEGORIES):
            major_category = MAJOR_CATEGORIES[int(major_input) - 1]
        else:
            print("1 또는 2를 입력해주세요.")
            continue

        existing_subs = list(dict.fromkeys(
            r["sub_category"] for r in recipes
            if r["major_category"] == major_category and r["sub_category"]
        ))
        if existing_subs:
            print("기존 소분류:")
            for i, s in enumerate(existing_subs, 1):
                print(f"  {i}. {s}")

        sub_input = input("소분류 (번호 선택, 새 이름 입력, 없으면 엔터, q: 메인 메뉴로): ").strip()
        if sub_input.lower() == "q":
            break
        if sub_input.isdigit() and existing_subs and 1 <= int(sub_input) <= len(existing_subs):
            sub_category = existing_subs[int(sub_input) - 1]
        else:
            sub_category = sub_input

        name = input("완제품 이름 (q: 메인 메뉴로): ").strip()
        if name.lower() == "q":
            break
        if not name:
            print("이름은 비워둘 수 없습니다.")
            continue

        if db.recipe_exists(by_name, name):
            print(f"'{name}'은(는) 이미 등록되어 있습니다.")
            continue

        output_raw = input("산출 수량 (기본 1, q: 메인 메뉴로): ").strip()
        if output_raw.lower() == "q":
            break
        try:
            output_qty = int(output_raw) if output_raw else 1
        except ValueError:
            print("산출 수량은 숫자로 입력해주세요.")
            continue
        if output_qty < 1:
            print("산출 수량은 1 이상이어야 합니다.")
            continue

        materials = input_materials(by_name, materials_db)
        if materials is None:
            break
        if not materials:
            print("재료가 없어 등록을 취소합니다.")
            continue

        db.add_recipe(recipes, by_name, major_category, sub_category, name, output_qty, materials)
        db.save_recipes(recipes)
        print(f"'{name}' 등록 완료.\n")


def cmd_find_by_product(by_name):
    while True:
        name = input("완제품 이름 (q: 메인 메뉴로): ").strip()
        if name.lower() == "q":
            break

        recipe = db.find_by_product(by_name, name)
        if recipe is None:
            print(f"'{name}'을(를) 찾을 수 없습니다.\n")
            continue

        sub = f"/{recipe['sub_category']}" if recipe["sub_category"] else ""
        print(f"[{recipe['major_category']}{sub}] {recipe['name']} (산출 {recipe['output_qty']}개)")
        for mat in recipe["materials"]:
            print(f"  - {mat['name']} x{mat['qty']}")
        print()


def cmd_find_by_material(by_material):
    while True:
        name = input("재료 이름 (q: 메인 메뉴로): ").strip()
        if name.lower() == "q":
            break

        products = db.find_products_using_material(by_material, name)
        if not products:
            print(f"'{name}'을(를) 사용하는 완제품이 없습니다.\n")
            continue

        print(f"'{name}'을(를) 사용하는 완제품:")
        for p in products:
            print(f"  - {p['name']} (필요 수량: {p['qty']})")
        print()


def cmd_breakdown(by_name):
    while True:
        name = input("완제품 이름 (q: 메인 메뉴로): ").strip()
        if name.lower() == "q":
            break

        if not db.recipe_exists(by_name, name):
            print(f"'{name}'을(를) 찾을 수 없습니다.\n")
            continue

        qty_raw = input("제작할 개수 (기본 1, q: 메인 메뉴로): ").strip()
        if qty_raw.lower() == "q":
            break
        try:
            qty = int(qty_raw) if qty_raw else 1
        except ValueError:
            print("개수는 숫자로 입력해주세요.\n")
            continue

        try:
            tree = db.breakdown_tree(by_name, name, qty)
        except ValueError as e:
            print(f"오류: {e}\n")
            continue

        processed, raw = db.summarize_requirements(tree)

        print(f"\n'{name}' {qty}개 제작 시 필요")

        print("\n[가공품]")
        if processed:
            for mat_name, info in processed.items():
                overage = "" if info["produced"] == info["qty"] else f" → {info['produced']}개 생산"
                print(f"  - {mat_name}: {info['qty']}개 (제작 {info['crafts']}회{overage})")
        else:
            print("  없음")

        print("\n[원재료]")
        if raw:
            for mat_name, mat_qty in raw.items():
                print(f"  - {mat_name}: {mat_qty}개")
        else:
            print("  없음")
        print()


def cmd_list_all(recipes):
    if not recipes:
        print("등록된 제작법이 없습니다.")
        return
    for r in recipes:
        sub = f"/{r['sub_category']}" if r["sub_category"] else ""
        print(f"[{r['major_category']}{sub}] {r['name']} (산출 {r['output_qty']}개)")


def cmd_edit_recipe(recipes, materials_db):
    while True:
        by_name, _ = db.build_indexes(recipes)

        name = input("수정할 완제품 이름 (q: 메인 메뉴로): ").strip()
        if name.lower() == "q":
            break

        recipe = db.find_by_product(by_name, name)
        if recipe is None:
            print(f"'{name}'을(를) 찾을 수 없습니다.\n")
            continue

        sub = f"/{recipe['sub_category']}" if recipe["sub_category"] else ""
        print(f"현재: [{recipe['major_category']}{sub}] {recipe['name']} (산출 {recipe['output_qty']}개)")
        for mat in recipe["materials"]:
            print(f"  - {mat['name']} x{mat['qty']}")
        print("(이름은 수정할 수 없습니다. 이름을 바꾸려면 삭제 후 다시 등록해주세요.)")

        print("대분류:")
        for i, m in enumerate(MAJOR_CATEGORIES, 1):
            print(f"  {i}. {m}")
        major_input = input(f"대분류 (번호 선택, 엔터=유지[{recipe['major_category']}], q: 메인 메뉴로): ").strip()
        if major_input.lower() == "q":
            break
        if not major_input:
            major_category = recipe["major_category"]
        elif major_input.isdigit() and 1 <= int(major_input) <= len(MAJOR_CATEGORIES):
            major_category = MAJOR_CATEGORIES[int(major_input) - 1]
        else:
            print("1 또는 2를 입력해주세요.\n")
            continue

        existing_subs = list(dict.fromkeys(
            r["sub_category"] for r in recipes
            if r["major_category"] == major_category and r["sub_category"]
        ))
        if existing_subs:
            print("기존 소분류:")
            for i, s in enumerate(existing_subs, 1):
                print(f"  {i}. {s}")
        sub_input = input(
            f"소분류 (번호 선택, 새 이름 입력, 엔터=유지[{recipe['sub_category'] or '없음'}], q: 메인 메뉴로): "
        ).strip()
        if sub_input.lower() == "q":
            break
        if not sub_input:
            sub_category = recipe["sub_category"]
        elif sub_input.isdigit() and existing_subs and 1 <= int(sub_input) <= len(existing_subs):
            sub_category = existing_subs[int(sub_input) - 1]
        else:
            sub_category = sub_input

        output_raw = input(f"산출 수량 (엔터=유지[{recipe['output_qty']}], q: 메인 메뉴로): ").strip()
        if output_raw.lower() == "q":
            break
        if not output_raw:
            output_qty = recipe["output_qty"]
        else:
            try:
                output_qty = int(output_raw)
            except ValueError:
                print("산출 수량은 숫자로 입력해주세요.\n")
                continue
            if output_qty < 1:
                print("산출 수량은 1 이상이어야 합니다.\n")
                continue

        change_materials = confirm_yes_no("재료를 다시 입력하시겠습니까? (y/N, q: 메인 메뉴로): ", allow_quit=True)
        if change_materials == "q":
            break
        if change_materials:
            materials = input_materials(by_name, materials_db)
            if materials is None:
                break
            if not materials:
                print("재료가 없어 수정을 취소합니다.\n")
                continue
        else:
            materials = recipe["materials"]

        db.update_recipe(recipe, major_category, sub_category, output_qty, materials)
        db.save_recipes(recipes)
        print(f"'{name}' 수정 완료.\n")


def cmd_complete_recipe(recipes, materials_db):
    while True:
        by_name, _ = db.build_indexes(recipes)
        stubs = [r for r in recipes if not r["materials"]]
        if not stubs:
            print("재료를 채워야 할 제작법이 없습니다.\n")
            return

        print("이름만 등록된 제작법:")
        for i, r in enumerate(stubs, 1):
            sub = f"/{r['sub_category']}" if r["sub_category"] else ""
            print(f"  {i}. [{r['major_category']}{sub}] {r['name']}")

        name_input = input("재료를 채울 제작법 번호 또는 이름 (q: 메인 메뉴로): ").strip()
        if name_input.lower() == "q":
            break

        if name_input.isdigit() and 1 <= int(name_input) <= len(stubs):
            recipe = stubs[int(name_input) - 1]
        else:
            recipe = next((r for r in stubs if r["name"] == name_input), None)
        if recipe is None:
            print("이름만 등록된 제작법 중에 찾을 수 없습니다.\n")
            continue

        existing_subs = list(dict.fromkeys(
            r["sub_category"] for r in recipes
            if r["major_category"] == recipe["major_category"] and r["sub_category"]
        ))
        if existing_subs:
            print("기존 소분류:")
            for i, s in enumerate(existing_subs, 1):
                print(f"  {i}. {s}")
        sub_input = input(
            f"소분류 (번호 선택, 새 이름 입력, 엔터=유지[{recipe['sub_category'] or '없음'}], q: 메인 메뉴로): "
        ).strip()
        if sub_input.lower() == "q":
            break
        if not sub_input:
            sub_category = recipe["sub_category"]
        elif sub_input.isdigit() and existing_subs and 1 <= int(sub_input) <= len(existing_subs):
            sub_category = existing_subs[int(sub_input) - 1]
        else:
            sub_category = sub_input

        output_raw = input(f"산출 수량 (엔터=유지[{recipe['output_qty']}], q: 메인 메뉴로): ").strip()
        if output_raw.lower() == "q":
            break
        if not output_raw:
            output_qty = recipe["output_qty"]
        else:
            try:
                output_qty = int(output_raw)
            except ValueError:
                print("산출 수량은 숫자로 입력해주세요.\n")
                continue
            if output_qty < 1:
                print("산출 수량은 1 이상이어야 합니다.\n")
                continue

        materials = input_materials(by_name, materials_db)
        if materials is None:
            break
        if not materials:
            print("재료가 없어 완성을 취소합니다.\n")
            continue

        db.update_recipe(recipe, recipe["major_category"], sub_category, output_qty, materials)
        db.save_recipes(recipes)
        print(f"'{recipe['name']}' 제작법 완성 완료.\n")


def cmd_delete_recipe(recipes):
    while True:
        by_name, by_material = db.build_indexes(recipes)

        name = input("삭제할 완제품 이름 (q: 메인 메뉴로): ").strip()
        if name.lower() == "q":
            break

        recipe = db.find_by_product(by_name, name)
        if recipe is None:
            print(f"'{name}'을(를) 찾을 수 없습니다.\n")
            continue

        sub = f"/{recipe['sub_category']}" if recipe["sub_category"] else ""
        print(f"[{recipe['major_category']}{sub}] {recipe['name']} (산출 {recipe['output_qty']}개)")
        for mat in recipe["materials"]:
            print(f"  - {mat['name']} x{mat['qty']}")

        users = db.find_products_using_material(by_material, name)
        if users:
            user_names = ", ".join(u["name"] for u in users)
            print(f"경고: 이 항목을 재료로 쓰는 완제품이 있습니다 -> {user_names}")

        confirm = confirm_yes_no(f"'{name}'을(를) 정말 삭제하시겠습니까? (y/N): ")
        if not confirm:
            print("취소했습니다.\n")
            continue

        db.remove_recipe(recipes, by_name, name)
        db.save_recipes(recipes)
        print(f"'{name}' 삭제 완료.\n")


def cmd_add_scroll(scrolls, recipes, by_name, materials_db):
    while True:
        types = list(dict.fromkeys(list(DEFAULT_SCROLL_TYPES) + [s["scroll_type"] for s in scrolls]))
        print("스크롤 종류:")
        for i, t in enumerate(types, 1):
            print(f"  {i}. {t}")

        type_input = input("스크롤 종류 (번호 선택, 새 이름 입력, q: 메인 메뉴로): ").strip()
        if type_input.lower() == "q":
            break

        if type_input.isdigit() and 1 <= int(type_input) <= len(types):
            scroll_type = types[int(type_input) - 1]
        else:
            scroll_type = type_input
        if not scroll_type:
            print("스크롤 종류를 입력해주세요.")
            continue

        existing_towns = list(dict.fromkeys(
            s["town"] for s in scrolls
            if s["scroll_type"] == scroll_type and s["town"]
        ))
        if existing_towns:
            print("기존 마을:")
            for i, t in enumerate(existing_towns, 1):
                print(f"  {i}. {t}")

        town_input = input("마을 (번호 선택, 새 이름 입력, q: 메인 메뉴로): ").strip()
        if town_input.lower() == "q":
            break
        if town_input.isdigit() and existing_towns and 1 <= int(town_input) <= len(existing_towns):
            town = existing_towns[int(town_input) - 1]
        else:
            town = town_input
        if not town:
            print("마을 이름을 입력해주세요.\n")
            continue

        target_name = input("대상 아이템 이름 (q: 메인 메뉴로): ").strip()
        if target_name.lower() == "q":
            break
        if not target_name:
            print("이름은 비워둘 수 없습니다.")
            continue

        ok, reason = db.validate_scroll_target(by_name, scroll_type, target_name)
        if not ok:
            print(reason)
            major = db.get_major_category(by_name, target_name)

            if scroll_type not in ("제작", "요리") or major is not None:
                print()
                continue

            add_now = confirm_yes_no(f"'{target_name}'을(를) 제작법에 이름만 먼저 등록해두시겠습니까? (y/N): ")
            if not add_now:
                print()
                continue

            db.add_recipe(recipes, by_name, "제작품", "", target_name, 1, [])
            db.save_recipes(recipes)
            print(f"'{target_name}' 이름만 제작법에 등록했습니다. (13. 제작법 재료 채우기에서 나중에 재료를 추가해주세요)\n")

        if scroll_type in ("채집", "채광") and not db.material_exists(materials_db, target_name):
            add_now = confirm_yes_no(f"'{target_name}'을(를) 원재료 목록에도 등록해두시겠습니까? (y/N): ")
            if add_now:
                db.add_material(materials_db, target_name)
                db.save_materials(materials_db)
                print(f"'{target_name}' 원재료로 등록했습니다.\n")

        if db.scroll_exists(scrolls, scroll_type, target_name):
            print(f"'{scroll_type} 스크롤: {target_name}'은(는) 이미 등록되어 있습니다.\n")
            continue

        qty_raw = input("스크롤 1장당 필요 수량 (q: 메인 메뉴로): ").strip()
        if qty_raw.lower() == "q":
            break
        try:
            qty_per_scroll = int(qty_raw)
        except ValueError:
            print("수량은 숫자로 입력해주세요.\n")
            continue

        db.add_scroll(scrolls, scroll_type, town, target_name, qty_per_scroll)
        db.save_scrolls(scrolls)
        print(f"'{scroll_type} 스크롤: {target_name}' ({town}) 등록 완료.\n")


def cmd_scroll_breakdown(scrolls, by_name):
    while True:
        types = list(dict.fromkeys(s["scroll_type"] for s in scrolls))
        if types:
            print("스크롤 종류:")
            for i, t in enumerate(types, 1):
                print(f"  {i}. {t}")

        type_input = input("스크롤 종류 (번호 선택 또는 이름 입력, q: 메인 메뉴로): ").strip()
        if type_input.lower() == "q":
            break

        if type_input.isdigit() and types and 1 <= int(type_input) <= len(types):
            scroll_type = types[int(type_input) - 1]
        else:
            scroll_type = type_input

        target_name = input("대상 아이템 이름 (q: 메인 메뉴로): ").strip()
        if target_name.lower() == "q":
            break

        scroll = db.find_scroll(scrolls, scroll_type, target_name)
        if scroll is None:
            print(f"'{scroll_type} 스크롤: {target_name}'을(를) 찾을 수 없습니다.\n")
            continue

        n_raw = input("스크롤 장수 (q: 메인 메뉴로): ").strip()
        if n_raw.lower() == "q":
            break
        try:
            n = int(n_raw)
        except ValueError:
            print("장수는 숫자로 입력해주세요.\n")
            continue

        total_target_qty = scroll["qty_per_scroll"] * n
        print(f"\n'{scroll_type} 스크롤: {target_name}' {n}장 -> {target_name} {total_target_qty}개 필요")

        try:
            tree = db.breakdown_tree(by_name, target_name, total_target_qty)
        except ValueError as e:
            print(f"오류: {e}\n")
            continue

        processed, raw = db.summarize_requirements(tree)

        print("\n[가공품]")
        if processed:
            for mat_name, info in processed.items():
                overage = "" if info["produced"] == info["qty"] else f" → {info['produced']}개 생산"
                print(f"  - {mat_name}: {info['qty']}개 (제작 {info['crafts']}회{overage})")
        else:
            print("  없음")

        print("\n[원재료]")
        if raw:
            for mat_name, mat_qty in raw.items():
                print(f"  - {mat_name}: {mat_qty}개")
        else:
            print("  없음")
        print()


def cmd_list_scrolls(scrolls):
    if not scrolls:
        print("등록된 스크롤이 없습니다.")
        return
    for s in scrolls:
        print(f"[{s['scroll_type']} 스크롤] {s['target_name']} (마을: {s['town'] or '미상'}, 1장당 {s['qty_per_scroll']}개)")


def cmd_edit_scroll(scrolls):
    while True:
        types = list(dict.fromkeys(s["scroll_type"] for s in scrolls))
        if types:
            print("스크롤 종류:")
            for i, t in enumerate(types, 1):
                print(f"  {i}. {t}")

        type_input = input("수정할 스크롤 종류 (번호 선택 또는 이름 입력, q: 메인 메뉴로): ").strip()
        if type_input.lower() == "q":
            break
        if type_input.isdigit() and types and 1 <= int(type_input) <= len(types):
            scroll_type = types[int(type_input) - 1]
        else:
            scroll_type = type_input

        target_name = input("대상 아이템 이름 (q: 메인 메뉴로): ").strip()
        if target_name.lower() == "q":
            break

        scroll = db.find_scroll(scrolls, scroll_type, target_name)
        if scroll is None:
            print(f"'{scroll_type} 스크롤: {target_name}'을(를) 찾을 수 없습니다.\n")
            continue

        print(
            f"현재: [{scroll['scroll_type']} 스크롤] {scroll['target_name']} "
            f"(마을: {scroll['town'] or '미상'}, 1장당 {scroll['qty_per_scroll']}개)"
        )
        print("(스크롤 종류/대상 아이템은 수정할 수 없습니다. 바꾸려면 삭제 후 다시 등록해주세요.)")

        existing_towns = list(dict.fromkeys(
            s["town"] for s in scrolls
            if s["scroll_type"] == scroll_type and s["town"]
        ))
        if existing_towns:
            print("기존 마을:")
            for i, t in enumerate(existing_towns, 1):
                print(f"  {i}. {t}")
        town_input = input(
            f"마을 (번호 선택, 새 이름 입력, 엔터=유지[{scroll['town'] or '없음'}], q: 메인 메뉴로): "
        ).strip()
        if town_input.lower() == "q":
            break
        if not town_input:
            town = scroll["town"]
        elif town_input.isdigit() and existing_towns and 1 <= int(town_input) <= len(existing_towns):
            town = existing_towns[int(town_input) - 1]
        else:
            town = town_input

        qty_raw = input(f"스크롤 1장당 필요 수량 (엔터=유지[{scroll['qty_per_scroll']}], q: 메인 메뉴로): ").strip()
        if qty_raw.lower() == "q":
            break
        if not qty_raw:
            qty_per_scroll = scroll["qty_per_scroll"]
        else:
            try:
                qty_per_scroll = int(qty_raw)
            except ValueError:
                print("수량은 숫자로 입력해주세요.\n")
                continue

        db.update_scroll(scroll, town, qty_per_scroll)
        db.save_scrolls(scrolls)
        print(f"'{scroll_type} 스크롤: {target_name}' 수정 완료.\n")


def cmd_delete_scroll(scrolls):
    while True:
        types = list(dict.fromkeys(s["scroll_type"] for s in scrolls))
        if types:
            print("스크롤 종류:")
            for i, t in enumerate(types, 1):
                print(f"  {i}. {t}")

        type_input = input("삭제할 스크롤 종류 (번호 선택 또는 이름 입력, q: 메인 메뉴로): ").strip()
        if type_input.lower() == "q":
            break
        if type_input.isdigit() and types and 1 <= int(type_input) <= len(types):
            scroll_type = types[int(type_input) - 1]
        else:
            scroll_type = type_input

        target_name = input("대상 아이템 이름 (q: 메인 메뉴로): ").strip()
        if target_name.lower() == "q":
            break

        scroll = db.find_scroll(scrolls, scroll_type, target_name)
        if scroll is None:
            print(f"'{scroll_type} 스크롤: {target_name}'을(를) 찾을 수 없습니다.\n")
            continue

        print(
            f"[{scroll['scroll_type']} 스크롤] {scroll['target_name']} "
            f"(마을: {scroll['town'] or '미상'}, 1장당 {scroll['qty_per_scroll']}개)"
        )
        confirm = confirm_yes_no("정말 삭제하시겠습니까? (y/N): ")
        if not confirm:
            print("취소했습니다.\n")
            continue

        db.remove_scroll(scrolls, scroll_type, target_name)
        db.save_scrolls(scrolls)
        print(f"'{scroll_type} 스크롤: {target_name}' 삭제 완료.\n")


def cmd_add_material(materials_db):
    while True:
        name = input("원재료 이름 (q: 메인 메뉴로): ").strip()
        if name.lower() == "q":
            break
        if not name:
            print("이름은 비워둘 수 없습니다.")
            continue

        if db.material_exists(materials_db, name):
            print(f"'{name}'은(는) 이미 등록되어 있습니다.\n")
            continue

        db.add_material(materials_db, name)
        db.save_materials(materials_db)
        print(f"'{name}' 원재료로 등록 완료.\n")


def cmd_list_materials(materials_db):
    if not materials_db:
        print("등록된 원재료가 없습니다.")
        return
    for name in materials_db:
        print(f"- {name}")


def cmd_delete_material(materials_db, by_material):
    while True:
        name = input("삭제할 원재료 이름 (q: 메인 메뉴로): ").strip()
        if name.lower() == "q":
            break

        if not db.material_exists(materials_db, name):
            print(f"'{name}'을(를) 찾을 수 없습니다.\n")
            continue

        users = db.find_products_using_material(by_material, name)
        if users:
            user_names = ", ".join(u["name"] for u in users)
            print(f"경고: 이 항목을 재료로 쓰는 완제품이 있습니다 -> {user_names}")

        confirm = confirm_yes_no(f"'{name}'을(를) 정말 삭제하시겠습니까? (y/N): ")
        if not confirm:
            print("취소했습니다.\n")
            continue

        db.remove_material(materials_db, name)
        db.save_materials(materials_db)
        print(f"'{name}' 삭제 완료.\n")


MENU = """
========================
1. 제작법 추가
2. 완제품 이름으로 재료 찾기
3. 재료로 완제품 역산
4. 완제품 n개 제작 시 가공품/원재료 집계
5. 전체 제작법 목록 보기
6. 스크롤 추가
7. 스크롤 필요 재료 역산
8. 전체 스크롤 목록 보기
9. 제작법 수정
10. 제작법 삭제
11. 스크롤 수정
12. 스크롤 삭제
13. 제작법 재료 채우기
14. 원재료 추가
15. 전체 원재료 목록 보기
16. 원재료 삭제
0. 종료
========================
"""


def main():
    recipes = db.load_recipes()
    by_name, by_material = db.build_indexes(recipes)
    scrolls = db.load_scrolls()
    materials_db = db.load_materials()

    while True:
        try:
            print(MENU)
            choice = input("선택: ").strip()

            if choice == "1":
                cmd_add(recipes, by_name, materials_db)
                by_name, by_material = db.build_indexes(recipes)
            elif choice == "2":
                cmd_find_by_product(by_name)
            elif choice == "3":
                cmd_find_by_material(by_material)
            elif choice == "4":
                cmd_breakdown(by_name)
            elif choice == "5":
                cmd_list_all(recipes)
            elif choice == "6":
                cmd_add_scroll(scrolls, recipes, by_name, materials_db)
                by_name, by_material = db.build_indexes(recipes)
            elif choice == "7":
                cmd_scroll_breakdown(scrolls, by_name)
            elif choice == "8":
                cmd_list_scrolls(scrolls)
            elif choice == "9":
                cmd_edit_recipe(recipes, materials_db)
                by_name, by_material = db.build_indexes(recipes)
            elif choice == "10":
                cmd_delete_recipe(recipes)
                by_name, by_material = db.build_indexes(recipes)
            elif choice == "11":
                cmd_edit_scroll(scrolls)
            elif choice == "12":
                cmd_delete_scroll(scrolls)
            elif choice == "13":
                cmd_complete_recipe(recipes, materials_db)
                by_name, by_material = db.build_indexes(recipes)
            elif choice == "14":
                cmd_add_material(materials_db)
            elif choice == "15":
                cmd_list_materials(materials_db)
            elif choice == "16":
                cmd_delete_material(materials_db, by_material)
            elif choice == "0":
                print("종료합니다.")
                break
            else:
                print("잘못된 선택입니다.")
        except UnicodeError:
            print("\n입력이 깨져서 인식할 수 없습니다 (터미널 인코딩 문제). 저장되지 않았으니 메인 메뉴부터 다시 시도해주세요.\n")


if __name__ == "__main__":
    main()
