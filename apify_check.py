import os
import sys
import json
import time
from typing import Dict, List, Optional, Tuple

import requests


def load_env() -> Dict[str, Optional[str]]:
    # Lazy load .env if present
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv()
    except Exception:
        pass

    return {
        "APIFY_TOKEN": os.getenv("APIFY_TOKEN"),
        "APIFY_ACTOR_IMMOSCOUT24": os.getenv("APIFY_ACTOR_IMMOSCOUT24"),
        "APIFY_ACTOR_IMMOWELT": os.getenv("APIFY_ACTOR_IMMOWELT"),
        "APIFY_ACTOR_KLEINANZEIGEN": os.getenv("APIFY_ACTOR_KLEINANZEIGEN"),
        "ALT_SCRAPER_TOKEN": os.getenv("ALT_SCRAPER_TOKEN"),
    }


def print_header(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def get(url: str) -> Tuple[int, str]:
    try:
        r = requests.get(url, timeout=30)
        return r.status_code, r.text
    except Exception as e:
        return -1, str(e)


def post_json(url: str, payload: Dict) -> Tuple[int, str]:
    try:
        r = requests.post(url, json=payload, timeout=60)
        return r.status_code, r.text
    except Exception as e:
        return -1, str(e)


def check_apify_me(token: str) -> None:
    print_header("Apify: Проверка токена /v2/me")
    code, body = get(f"https://api.apify.com/v2/me?token={token}")
    print(f"GET /v2/me → {code}")
    if code == 200:
        try:
            data = json.loads(body)
            username = data.get("data", {}).get("username")
            plan = data.get("data", {}).get("plan")
            print(f"✔ Токен валиден. Аккаунт: {username} | План: {plan}")
        except Exception:
            print("✔ Токен валиден (парсинг ответа не удался, но статус 200)")
    elif code == 401:
        print("✖ 401 Unauthorized — неверный APIFY_TOKEN")
    else:
        print(f"✖ Неожиданный ответ: {body[:400]}")


def check_actor_meta(token: str, actor_id: str) -> None:
    print_header(f"Apify: Проверка метаданных актора {actor_id}")
    code, body = get(f"https://api.apify.com/v2/acts/{actor_id}?token={token}")
    print(f"GET /v2/acts/{actor_id} → {code}")
    if code == 200:
        print("✔ Актор доступен этому токену")
    elif code == 404:
        print("✖ 404 Not Found — actorId некорректен или нет доступа этим токеном")
    elif code == 401:
        print("✖ 401 Unauthorized — токен не принят (проверьте APIFY_TOKEN)")
    else:
        print(f"✖ Неожиданный ответ: {body[:400]}")


def try_run_actor_with_payloads(token: str, actor_id: str, payloads: List[Tuple[str, Dict]]) -> None:
    print_header(f"Apify: Запуск актора {actor_id}")
    run_url = f"https://api.apify.com/v2/acts/{actor_id}/runs?token={token}"
    for label, payload in payloads:
        print(f"→ Пытаюсь payload: {label}")
        code, body = post_json(run_url, payload)
        print(f"POST /v2/acts/{actor_id}/runs → {code}")
        if code in (200, 201):
            print("✔ Запуск принят. Актор стартовал.")
            return
        if code == 402:
            print("✖ 402 Payment Required — лимиты/кредиты/подписка. Это тариф, не код.")
            print(body[:400])
            return
        if code == 400:
            print("✖ 400 Bad Request — актор не принял вход. Нужна корректировка полей input.")
            print(body[:400])
        elif code == 404:
            print("✖ 404 Not Found — ID не найден или недоступен этому токену.")
        elif code == 401:
            print("✖ 401 Unauthorized — токен не принят API.")
        else:
            print(f"✖ Неожиданный ответ ({code}): {body[:400]}")
    print("Итог: ни один payload не запустил актор (см. ошибки выше).")


def build_payloads_for_actor(actor_id: str, city: str, price_max: Optional[int], rooms_max: Optional[int]) -> List[Tuple[str, Dict]]:
    city_slug = (city or "berlin").lower()

    # Common minimal payloads used by многие акторы на Immowelt/Kleinanzeigen
    immowelt_url = f"https://www.immowelt.de/liste/{city_slug}/wohnungen/mieten"
    klein_url = f"https://www.kleinanzeigen.de/s-wohnung-mieten/{city_slug}/k0"

    payloads: List[Tuple[str, Dict]] = []

    # Generic variants
    payloads.append((
        "start_urls (snake) + limit",
        {
            "start_urls": [{"url": immowelt_url}],
            "scrape_page_limit": 1,
            "maxItems": 10,
        },
    ))
    payloads.append((
        "startUrls (camel) + limit",
        {
            "startUrls": [immowelt_url],
            "scrapePageLimit": 1,
            "maxItems": 10,
        },
    ))
    payloads.append((
        "kleinanzeigen start URL",
        {
            "startUrls": [klein_url],
            "maxItems": 10,
        },
    ))
    payloads.append((
        "searchQuery",
        {
            "searchQuery": city_slug,
            "maxItems": 10,
        },
    ))

    # Actor-specific hints
    if "immowelt" in actor_id:
        payloads.insert(0, (
            "immowelt minimal",
            {
                "start_urls": [{"url": immowelt_url}],
                "scrape_page_limit": 1,
            },
        ))

    if "klein" in actor_id:
        payloads.insert(0, (
            "kleinanzeigen minimal",
            {
                "startUrls": [klein_url],
                "maxItems": 10,
            },
        ))

    if "immoscout" in actor_id:
        # API-actor у ImmoScout24 часто ждёт массив detail-URL; мы пробуем явно неправильный
        payloads = [
            (
                "is24 detail urls (example)",
                {
                    "urls": [
                        "https://www.immobilienscout24.de/expose/123456789"
                    ]
                },
            )
        ] + payloads

    return payloads


def check_zenrows(token: Optional[str]) -> None:
    print_header("Zenrows: Проверка токена")
    if not token:
        print("(пропущено) ALT_SCRAPER_TOKEN не задан")
        return
    test_url = f"https://api.zenrows.com/v1/?url=https%3A%2F%2Fexample.com&apikey={token}"
    code, body = get(test_url)
    print(f"GET /v1/?url=example.com → {code}")
    if code == 200:
        print("✔ Токен Zenrows работает")
    elif code in (401, 403):
        print("✖ 401/403 — токен неверный или запрещён")
        print(body[:400])
    elif code == 402:
        print("✖ 402 Payment Required — нет квоты/тариф отключён")
        print(body[:400])
    else:
        print(f"✖ Неожиданный ответ: {body[:400]}")


def main() -> None:
    env = load_env()

    apify_token = env.get("APIFY_TOKEN")
    is24_id = env.get("APIFY_ACTOR_IMMOSCOUT24")
    immowelt_id = env.get("APIFY_ACTOR_IMMOWELT")
    klein_id = env.get("APIFY_ACTOR_KLEINANZEIGEN")
    zenrows_token = env.get("ALT_SCRAPER_TOKEN")

    city = os.getenv("DEFAULT_CITY", "Berlin")
    try:
        price_max = int(os.getenv("MAX_PRICE_CAP", "5000"))
    except Exception:
        price_max = 5000
    rooms_max = None

    if not apify_token:
        print("✖ APIFY_TOKEN не найден в .env — добавьте и повторите")
        sys.exit(1)

    check_apify_me(apify_token)

    # Actors metadata
    for actor_id in [immowelt_id, klein_id, is24_id]:
        if actor_id:
            check_actor_meta(apify_token, actor_id)

    # Try to run each actor with a set of payloads
    if immowelt_id:
        payloads = build_payloads_for_actor(immowelt_id, city, price_max, rooms_max)
        try_run_actor_with_payloads(apify_token, immowelt_id, payloads)

    if klein_id:
        payloads = build_payloads_for_actor(klein_id, city, price_max, rooms_max)
        try_run_actor_with_payloads(apify_token, klein_id, payloads)

    if is24_id:
        payloads = build_payloads_for_actor(is24_id, city, price_max, rooms_max)
        try_run_actor_with_payloads(apify_token, is24_id, payloads)

    # Zenrows
    check_zenrows(zenrows_token)

    print("\nГотово. Смотрите статусы выше (200/201 — ок, 400 — input, 402 — тариф/кредиты, 404 — ID/доступ).")


if __name__ == "__main__":
    main()


