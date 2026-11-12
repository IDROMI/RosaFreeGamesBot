
import os
import json
import logging
import requests

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)

TOKEN = os.getenv("TELEGRAM_TOKEN")

logging.basicConfig(level=logging.INFO)

EPIC_URL = (
    "https://store-site-backend-static.ak.epicgames.com/"
    "freeGamesPromotions?locale=pt-PT&country=PT&allowCountries=PT"
)

STEAM_URL = (
    "https://store.steampowered.com/api/featuredcategories/"
    "?cc=pt&l=portuguese"
)

CHAT_FILE = "chats.json"
SEEN_FILE = "seen.json"


def load_json(filename):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f)


def get_epic_games():
    response = requests.get(EPIC_URL, timeout=20)
    response.raise_for_status()

    data = response.json()
    games = data["data"]["Catalog"]["searchStore"]["elements"]

    results = []

    for game in games:
        promotions = game.get("promotions") or {}
        offers = promotions.get("promotionalOffers") or []

        for group in offers:
            for offer in group.get("promotionalOffers", []):
                price = game.get("price", {}).get("totalPrice", {})

                if price.get("discountPrice") == 0:
                    title = game.get("title", "Jogo")
                    slug = game.get("productSlug") or game.get("urlSlug")

                    results.append({
                        "id": game["id"],
                        "name": title,
                        "url": (
                            "https://store.epicgames.com/pt-BR/p/"
                            + str(slug)
                            if slug else "https://store.epicgames.com/"
                        ),
                        "store": "Epic Games"
                    })

    return results


def get_steam_games():
    response = requests.get(STEAM_URL, timeout=20)
    response.raise_for_status()

    data = response.json()
    results = []

    for category in data.values():
        if not isinstance(category, dict):
            continue

        for game in category.get("items", []):
            if game.get("final_price") == 0:
                results.append({
                    "id": str(game.get("id")),
                    "name": game.get("name", "Jogo"),
                    "url": (
                        "https://store.steampowered.com/app/"
                        + str(game.get("id"))
                    ),
                    "store": "Steam"
                })

    return results


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    chats = load_json(CHAT_FILE)

    if chat_id not in chats:
        chats.append(chat_id)
        save_json(CHAT_FILE, chats)

    await update.message.reply_text(
        "🎮 Bem-vindo ao RosaFreeGamesBot!\n\n"
        "Vou procurar jogos gratuitos na Epic Games e Steam.\n"
        "Quando encontrar novidades, aviso-te aqui! 🚀"
    )


async def check_games(context: ContextTypes.DEFAULT_TYPE):
    chats = load_json(CHAT_FILE)
    seen = load_json(SEEN_FILE)

    try:
        games = get_epic_games() + get_steam_games()

        for game in games:
            game_id = game["store"] + "_" + game["id"]

            if game_id in seen:
                continue

            message = (
                "🎮 NOVO JOGO GRÁTIS!\n\n"
                f"🏪 Loja: {game['store']}\n"
                f"🎁 Jogo: {game['name']}\n\n"
                f"🔗 {game['url']}"
            )

            for chat_id in chats:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=message
                )

            seen.append(game_id)

        save_json(SEEN_FILE, seen)

    except Exception:
        logging.exception("Erro ao verificar jogos gratuitos")


def main():
    if not TOKEN:
        raise RuntimeError("Falta configurar TELEGRAM_TOKEN")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.job_queue.run_repeating(
        check_games,
        interval=21600,
        first=10
    )

    print("RosaFreeGamesBot iniciado!")

    app.run_polling()


if __name__ == "__main__":
    main()
