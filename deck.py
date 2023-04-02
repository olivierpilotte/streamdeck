#!/usr/bin/env python3

import json
import os
import subprocess
import threading

from PIL import Image, ImageDraw, ImageFont
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ImageHelpers import PILHelper


ASSETS_PATH = os.path.join(os.path.dirname(__file__), "assets")

CURRENT_PAGE = 0

# examples
# "command": ["qute", ":tab-select 0/1"]

current_dir = os.path.dirname(os.path.abspath(__file__))
apps_file_path = os.path.join(current_dir, 'apps.json')

with open(apps_file_path, "r") as file:
    apps = json.loads(file.read())


def render_key_image(deck, icon_filename, font_filename, label_text):
    icon = Image.open(icon_filename)
    image = PILHelper.create_scaled_image(deck, icon, margins=[0, 0, 30, 0])

    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(font_filename, 14)
    draw.text((image.width / 2, image.height - 5), text=label_text, font=font, anchor="ms", fill="white")

    return PILHelper.to_native_format(deck, image)


def get_key_style(deck, key, state):
    global CURRENT_PAGE

    if "name" not in apps[CURRENT_PAGE][key]:
        return False

    name = apps[CURRENT_PAGE][key]["name"]

    icon = f"{name}.png"
    font = "Roboto-Regular.ttf"

    return {
        "name": name,
        "icon": os.path.join(ASSETS_PATH, icon),
        "font": os.path.join(ASSETS_PATH, font),
        "label": ""
    }


def update_key_image(deck, key, state):
    global CURRENT_PAGE

    if "name" not in apps[CURRENT_PAGE][key]:
        return False

    key_style = get_key_style(deck, key, state)
    image = render_key_image(deck, key_style["icon"], key_style["font"], key_style["label"])

    with deck:
        deck.set_key_image(key, image)


def key_change_callback(deck, key, state):
    global CURRENT_PAGE

    # Print new key state
    # print("Deck {} Key {} = {}".format(deck.id(), key, state), flush=True)

    update_key_image(deck, key, state)

    if state:
        key_style = get_key_style(deck, key, state)
        if not key_style:
            return

        match key_style["name"]:
            case "exit":
                with deck:
                    deck.reset()
                    deck.close()

            case "reload":
                with deck:
                    deck.reset()
                    init(deck)

            case "up":
                subprocess.Popen(["i3-msg", "focus", "up"])

            case "down":
                subprocess.Popen(["i3-msg", "focus", "down"])

            case "left":
                # subprocess.Popen(["i3-msg", "focus", "left"])
                if (CURRENT_PAGE) > 0:
                    CURRENT_PAGE -= 1

                    with deck:
                        deck.reset()
                        init(deck)

            case "right":
                # subprocess.Popen(["i3-msg", "focus", "right"])
                if CURRENT_PAGE < (len(apps) - 1):
                    CURRENT_PAGE += 1

                    with deck:
                        deck.reset()
                        init(deck)

            case _:
                with open("/tmp/bob.txt", "w") as file:
                    subprocess.Popen(
                        apps[CURRENT_PAGE][key]["command"],
                        stdout=file,
                        stderr=file
                    )


def init(deck):
    global apps
    global apps_file_path

    with open(apps_file_path, "r") as file:
        apps = json.loads(file.read())

    for key in range(deck.key_count()):
        update_key_image(deck, key, False)


if __name__ == "__main__":
    decks = []

    try:
        streamdecks = DeviceManager().enumerate()

        print("Found {} Stream Deck(s).\n".format(len(streamdecks)))

        for index, deck in enumerate(streamdecks):
            if not deck.is_visual():
                continue

            decks.append(deck)

            deck.open()
            deck.reset()

            print("Opened '{}' device (serial number: '{}', fw: '{}')".format(
                deck.deck_type(), deck.get_serial_number(), deck.get_firmware_version()
            ))

            deck.set_brightness(50)
            deck.set_key_callback(key_change_callback)

            init(deck)

            for t in threading.enumerate():
                try:
                    t.join()
                except RuntimeError:
                    pass

    except Exception as e:
        print(e)

        for deck in decks:
            with deck:
                deck.reset()
                deck.close()
