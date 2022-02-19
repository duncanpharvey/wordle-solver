from wordfreq import zipf_frequency
import collections


def getWords():
    words = []
    f = open("all-words.txt", "r")
    for line in f:
        word = line.strip()
        frequency = zipf_frequency(word, 'en')
        if frequency == 0:  # remove words with a frequency score of 0 from the potential word list
            continue
        words.append(word)
    return words


def getWordScores(words):
    letterSummary = {}
    for word in words:
        for letter in list(word):
            if not letter in letterSummary:
                letterSummary[letter] = 1
            else:
                letterSummary[letter] += 1
    wordScores = {}
    for word in words:
        score = 0
        for letter in set(word):  # only count unique letters towards score
            score += letterSummary[letter]
        score *= zipf_frequency(word, 'en')
        wordScores[word] = round(score, 2)
    return wordScores


def filterWords(words, guessedWord, states):
    possibleWords = []
    for word in words:
        # letter count for guessed letters in absent or present positions
        letterPool = collections.Counter(
            letter for letter, state in zip(word, states) if state != "correct")
        for letter, guessedLetter, state in zip(word, guessedWord, states):
            # possible word and guessed word do not have matching letter in this position when the tile state is correct
            if state == "correct" and letter != guessedLetter:
                break
            # possible word and guessed word have a matching letter in this position when the tile state is not correct
            elif state != "correct" and letter == guessedLetter:
                break
            elif state == "present":
                # possible word does not have the guessed letter in this position present in the rest of the word after accounting for the letters in correct positions
                if not letterPool[guessedLetter]:
                    break
                letterPool[guessedLetter] -= 1
            # possible word has an absent letter
            elif state == "absent" and letterPool[guessedLetter]:
                break
        else:
            # add possible word if no break from inner for loop
            possibleWords.append(word)
    return possibleWords


def getStates(secretWord, guessedWord):
    letterPool = collections.Counter(secretLetter for secretLetter, guessedLetter in zip(
        secretWord, guessedWord) if secretLetter != guessedLetter)  # letter count for secret letters in absent or present positions
    states = []
    for secretLetter, guessedLetter in zip(secretWord, guessedWord):
        if secretLetter == guessedLetter:
            states.append("correct")
        elif guessedLetter in secretWord and letterPool[guessedLetter] > 0:
            states.append("present")
            letterPool[guessedLetter] -= 1
        else:
            states.append("absent")

    return states
