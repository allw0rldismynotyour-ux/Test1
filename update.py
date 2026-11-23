# -*- coding: utf-8 -*-
"""
Обновление проекта Broken Arrow из GitHub.
Запускайте этот файл в Pydroid 3 из папки игры.
Использует только стандартную библиотеку Python.
"""
import json
import os
import sys
import urllib.request
import urllib.error

OWNER = "allw0rldismynotyour-ux"
REPO = "Test1"
BRANCH = "main"

# Обновляются только эти файлы игры. Карта custom_map.json и другие
# пользовательские данные не затрагиваются.
MANAGED_FILES = {
    "main.py",
    "map.py",
    "soldier.py",
    "btr80.py",
    "demo_btr80.py",
}

BASE_API = "https://api.github.com/repos/{}/{}/contents/{}"


def request(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "BrokenArrow-Pydroid-Updater",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(req, timeout=25) as response:
        return response.read()


def update():
    folder = os.path.dirname(os.path.abspath(__file__))
    print("Проверяю GitHub...")

    api_url = BASE_API.format(OWNER, REPO, "") + "?ref=" + BRANCH
    try:
        entries = json.loads(request(api_url).decode("utf-8"))
    except Exception as exc:
        print("Не удалось связаться с GitHub:", exc)
        print("Проверь интернет и повтори запуск.")
        return

    remote_files = {
        item["name"]: item["download_url"]
        for item in entries
        if item.get("type") == "file"
        and item.get("name") in MANAGED_FILES
        and item.get("download_url")
    }

    if not remote_files:
        print("В репозитории пока нет файлов игры для обновления.")
        return

    updated = []
    for name, url in sorted(remote_files.items()):
        try:
            data = request(url)
            target = os.path.join(folder, name)
            temp = target + ".update_tmp"

            with open(temp, "wb") as file:
                file.write(data)

            # Атомарная замена: старый файл не пропадёт при неудачной загрузке.
            os.replace(temp, target)
            updated.append(name)
            print("Обновлён:", name)
        except Exception as exc:
            try:
                if os.path.exists(temp):
                    os.remove(temp)
            except Exception:
                pass
            print("Ошибка файла {}: {}".format(name, exc))

    if updated:
        print("\nГотово. Обновлено файлов:", len(updated))
        print("Теперь можно запускать main.py.")
    else:
        print("Ничего не обновлено.")


if __name__ == "__main__":
    update()
