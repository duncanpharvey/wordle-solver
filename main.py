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
    f = open("stanford-words.txt", "r") # https://www-cs-faculty.stanford.edu/~knuth/sgb.html
    for line in f:
        word = line.strip()
        frequency = zipf_frequency(word, 'en')
        if frequency == 0: # remove words with a frequency score of 0 from the potential word list
            continue
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
    for word in words:
        score = 0
        for letter in set(word): # only count unique letters towards score
            score += letterSummary[letter]
        score *= zipf_frequency(word, 'en')
        wordScores[word] = round(score, 2)
    return wordScores


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
    wordScores = getWordScores(words, letterSummary)
    candidateWords = sorted(wordScores.items(), key=lambda item: item[1], reverse = True)[:40]
    print("candidate words:", dict(candidateWords))

    index = randint(0, 39)
    word = candidateWords[index][0]
    print("first word selected randomly from 40 candidate words:", word, "\n")

    try:
        browser = await launch({"headless":False, "args" : ['--window-size=720,1080', "--window-position=0,0"]})
        [page] = await browser.pages()
        await page.goto('https://www.powerlanguage.co.uk/wordle/')
        await page.evaluate("document.querySelector('game-app').shadowRoot.querySelector('game-modal').shadowRoot.querySelector('game-icon').click()")
    except:
        print("error navigating to wordle page")
        return

    await browser._connection.send('Browser.grantPermissions', { 'origin': 'https://www.powerlanguage.co.uk/wordle/', 'permissions': ['clipboardRead', 'clipboardWrite'] })

    for row in range(6):
        time.sleep(1) # buffer to give Wordle time to render

        try:
            await page.keyboard.type(word, delay=100)
            await page.keyboard.press('Enter', delay=100)
        except:
            print("error typing word")
            return

        # wait until the last letter has a state before continuing
        try:
            await page.waitForFunction(f"() => document.querySelector('game-app').shadowRoot.querySelectorAll('game-row')[{row}].shadowRoot.querySelectorAll('game-tile')[4].shadowRoot.querySelector('.tile[data-state=\"absent\"], .tile[data-state=\"present\"], .tile[data-state=\"correct\"]')")
        except:
            print("error waiting for letters to be evaluated")
            return

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

        print("results from wordle:", states)

        incorrectLetters, correctLetters, correctLetterPos, incorrectLetterPos = processGuessResult(states, word, incorrectLetters, correctLetters, correctLetterPos, incorrectLetterPos)
        print("incorrect letters:", incorrectLetters)
        print("correct letters:", correctLetters)
        print("letters in correct positions:", correctLetterPos)
        print("letters in incorrect positions:", incorrectLetterPos)     

        words, letterSummary = getPossibleWords(words, incorrectLetters, correctLetters, correctLetterPos, incorrectLetterPos)
        wordScores = getWordScores(words, letterSummary)
        candidateWords = sorted(wordScores.items(), key=lambda item: item[1], reverse = True)
        print("candidate words:", dict(candidateWords))

        word = candidateWords[0][0]
        print("next word:", word, "\n")

    await page.waitForFunction("document.querySelector('game-app').shadowRoot.querySelector('game-stats')")
    await page.evaluate("document.querySelector('game-app').shadowRoot.querySelector('game-stats').shadowRoot.getElementById('share-button').click()")

    text = await page.evaluate("navigator.clipboard.readText()")
    requests.post(os.environ["WORDLE_BOT_SLACK_WEBHOOK_HOTEL_HARVEY"], data=json.dumps({ 'text': text }))
    print(text)

    try:
        await browser.close()
    except:
        print("error while closing browser")

asyncio.get_event_loop().run_until_complete(main())
