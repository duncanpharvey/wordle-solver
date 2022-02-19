import asyncio
from pyppeteer import launch
import time
import json
import requests
import os
from dotenv import load_dotenv
from words import getWords, getWordScores, filterWords

load_dotenv()

async def main():
    words = getWords()

    try:
        browser = await launch({"headless":False, "args" : ['--window-size=720,1080', "--window-position=0,0"]})
        [page] = await browser.pages()
        await page.goto('https://www.nytimes.com/games/wordle/index.html')
        await page.evaluate("document.querySelector('game-app').shadowRoot.querySelector('game-modal').shadowRoot.querySelector('game-icon').click()")
    except:
        print("error navigating to wordle page")
        return

    await browser._connection.send('Browser.grantPermissions', { 'origin': 'https://www.nytimes.com/games/wordle/index.html', 'permissions': ['clipboardRead', 'clipboardWrite'] })

    for row in range(6):
        wordScores = getWordScores(words)
        candidateWords = sorted(wordScores.items(), key=lambda item: item[1], reverse=True)
        if len(candidateWords) == 0:
            print("no candidate words left")
            return
        print("candidate words:", dict(candidateWords[:40]))

        guessedWord = candidateWords[0][0]
        print("next word:", guessedWord)

        time.sleep(1) # buffer to give Wordle time to render

        try:
            await page.keyboard.type(guessedWord, delay=100)
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

        states = []
        for col in range(5):
            try:
                state = await page.evaluate(f"document.querySelector('game-app').shadowRoot.querySelectorAll('game-row')[{row}].shadowRoot.querySelectorAll('game-tile')[{col}].shadowRoot.querySelector('.tile').getAttribute('data-state')")
            except:
                print("error while getting letter states")
                return
            states.append(state)

        print("results from wordle:", states, "\n")
        if all(state == "correct" for state in states):
            print("woohoo!")
            break

        words = filterWords(words, guessedWord, states)

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
