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

f = open("solution-words.txt", "r")
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

max_guess_len = len(max(map(lambda x: str(x), results.keys()), key=len))
max_solution_len = len(max(map(lambda x: str(x), results.values()), key=len))

print('| Guess Count | Wordle Solution Count |')
print('| {} | {} |'.format('-' * max_guess_len, '-' * max_solution_len))

weighted_sum = 0
for key in sorted(results):
    print('|', key, '|', str(results[key]).ljust(max_solution_len, ' '), '|')
    weighted_sum += key * results[key]

print('\nWeighted Mean: `{}`'.format(round(weighted_sum / count, 4)))
