from autocorrect import Speller


spell = Speller(lang="en")


def autocorrect_message(message):
    words = message.split()
    final = []

    for word in words:
        corrected = spell(word)
        final.append((word, corrected))

    return final