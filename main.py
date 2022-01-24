import asyncio
from pyppeteer import launch
import time
from random import randint
import json
import requests
import os
from dotenv import load_dotenv

load_dotenv()

from wordfreq import zipf_frequency

def getWords():
    words = []
    f = open("words.txt", "r") # https://www-cs-faculty.stanford.edu/~knuth/sgb.html
    for line in f:
        word = line.strip()
        words.append(word)
    return set(words)


def getPossibleWords(words, incorrectLetters, correctLetters, correctLetterPos, incorrectLetterPos):
    possibleWords = set()
    letterSummary = {}
    for word in words:
        letterSet = set(word)
        # remove words that don't have all of the correct letters
        if not correctLetters.issubset(letterSet):
            continue
        # remove words that have any of the guessed letters that are incorrect
        if len(incorrectLetters.intersection(letterSet)) > 0:
            continue
        letterList = list(word)
        match = True
        # remove words that do not have letters in the correct positions
        for pos in range(5):
            letter = letterList[pos]
            if pos in correctLetterPos and letter != correctLetterPos[pos]:
                match = False
                break
            if pos in incorrectLetterPos and letter in incorrectLetterPos[pos]:
                match = False
                break
        if not match:
            continue
        possibleWords.add(word)
        for letter in letterList:
            if not letter in letterSummary:
                letterSummary[letter] = 1
            else:
                letterSummary[letter] += 1
    return possibleWords, letterSummary


def getWordScores(words, letterSummary):
    wordScores = {}
    maximum = (0, None)
    for word in words:
        score = 0
        for letter in set(word): # only count unique letters towards score
            score += letterSummary[letter]
        score *= zipf_frequency(word, 'en')
        if score > maximum[0]:
            maximum = (score, word)
        wordScores[word] = score
    return maximum[1], wordScores


# absent, present, correct
def processGuessResult(states, word, incorrectLetters, correctLetters, correctLetterPos, incorrectLetterPos):
    for pos in states["correct"]:
        letter = word[pos]
        correctLetters.add(letter)
        correctLetterPos[pos] = letter
    for pos in states["present"]:
        letter = word[pos]
        correctLetters.add(letter)
        incorrectLetterPos[pos].add(letter)
    for pos in states["absent"]:
        letter = word[pos]
        if letter in correctLetters: # handle edge case when a word has the same letter match multiple times
            incorrectLetterPos[pos].add(letter)
            continue
        incorrectLetters.add(letter)
    return incorrectLetters, correctLetters, correctLetterPos, incorrectLetterPos

async def main():
    incorrectLetters = set([])
    correctLetters = set([])
    correctLetterPos = {}
    incorrectLetterPos = {
        0: set([]),
        1: set([]),
        2: set([]),
        3: set([]),
        4: set([])
    }

    words = getWords()
    words, letterSummary = getPossibleWords(words, incorrectLetters, correctLetters, correctLetterPos, incorrectLetterPos)
    word, wordScores = getWordScores(words, letterSummary)
    print(dict(sorted(wordScores.items(), key=lambda item: item[1], reverse = True)[:40]))

    index = randint(0, 39)
    word = sorted(wordScores.items(), key=lambda item: item[1], reverse = True)[index][0]
    print(word)

    try:
        browser = await launch(headless=False)
        page = await browser.newPage()
        await page.goto('https://www.powerlanguage.co.uk/wordle/')
        await page.evaluate("document.querySelector('game-app').shadowRoot.querySelector('game-modal').shadowRoot.querySelector('game-icon').click()")
    except:
        print("error navigating to wordle page")
        return
    await browser._connection.send('Browser.grantPermissions', { 'origin': 'https://www.powerlanguage.co.uk/wordle/', 'permissions': ['clipboardRead', 'clipboardWrite'] })
    for row in range(6):
        time.sleep(1)
        try:
            await page.keyboard.type(word, delay=100)
            await page.keyboard.press('Enter', delay=100)
        except:
            print("error typing word")
            return

        # wait until all letters have a state in keyboard before moving on
        try:
            await page.waitForFunction(f"() => document.querySelector('game-app').shadowRoot.querySelectorAll('game-row')[{row}].shadowRoot.querySelectorAll('game-tile')[4].shadowRoot.querySelector('.tile[data-state=\"absent\"], .tile[data-state=\"present\"], .tile[data-state=\"correct\"]')")
        except:
            print("error waiting for letters to be evaluated")
            return

        # await page.waitForFunction(f"() => document.querySelector('game-app').shadowRoot.querySelector('game-keyboard').shadowRoot.querySelector('[data-key=\"{word[0]}\"][data-state]') && document.querySelector('game-app').shadowRoot.querySelector('game-keyboard').shadowRoot.querySelector('[data-key=\"{word[1]}\"][data-state]') && document.querySelector('game-app').shadowRoot.querySelector('game-keyboard').shadowRoot.querySelector('[data-key=\"{word[2]}\"][data-state]') && document.querySelector('game-app').shadowRoot.querySelector('game-keyboard').shadowRoot.querySelector('[data-key=\"{word[3]}\"][data-state]') && document.querySelector('game-app').shadowRoot.querySelector('game-keyboard').shadowRoot.querySelector('[data-key=\"{word[4]}\"][data-state]')")
        states = { "correct": [], "present": [], "absent": [] }
        for col in range(5):
            try:
                state = await page.evaluate(f"document.querySelector('game-app').shadowRoot.querySelectorAll('game-row')[{row}].shadowRoot.querySelectorAll('game-tile')[{col}].shadowRoot.querySelector('.tile').getAttribute('data-state')")
            except:
                print("error while getting letter states")
                return
            states[state].append(col)

        if len(states["correct"]) == 5:
            print("woohoo!")
            break

        print(states)
        incorrectLetters, correctLetters, correctLetterPos, incorrectLetterPos = processGuessResult(states, word, incorrectLetters, correctLetters, correctLetterPos, incorrectLetterPos)
        print(incorrectLetters, correctLetters, correctLetterPos, incorrectLetterPos)
        words, letterSummary = getPossibleWords(words, incorrectLetters, correctLetters, correctLetterPos, incorrectLetterPos)
        word, wordScores = getWordScores(words, letterSummary)
        print(dict(sorted(wordScores.items(), key=lambda item: item[1], reverse = True)))
        # word = input("enter word: ")

    await page.waitForFunction("document.querySelector('game-app').shadowRoot.querySelector('game-stats')")
    await page.evaluate("document.querySelector('game-app').shadowRoot.querySelector('game-stats').shadowRoot.getElementById('share-button').click()")
    text = await page.evaluate("navigator.clipboard.readText()")
    requests.post(os.environ["WORDLE_BOT_SLACK_WEBHOOK"], data=json.dumps({ 'text': text }))
    print(text)

    try:
        await browser.close()
    except:
        print("error while closing browser")

asyncio.get_event_loop().run_until_complete(main())
