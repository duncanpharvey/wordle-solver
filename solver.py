from words import getWords, getWordScores, getStates, filterWords


def guessWord(secretWord):
    words = getWords()

    numGuesses = 0
    while True:
        wordScores = getWordScores(words)
        candidateWords = sorted(wordScores.items(), key=lambda item: item[1], reverse=True)

        if len(candidateWords) == 0:
            print(secretWord, "no candidate words left")
            return 0

        guessedWord = candidateWords[0][0]
        numGuesses += 1

        states = getStates(secretWord, guessedWord)
        if all(state == "correct" for state in states):
            break

        words = filterWords(words, guessedWord, states)

    return numGuesses

results = {}

f = open("wordle-words.txt", "r")
count = 0
for line in f:
    count += 1
    word = line.strip()
    numGuesses = guessWord(word)

    if numGuesses not in results:
        results[numGuesses] = 1
    else:
        results[numGuesses] += 1
    
    if count % 100 == 0:
        print(count)

print(results)
