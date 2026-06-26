import nltk

# Tokenizers
from nltk.tokenize import (
    WhitespaceTokenizer,
    WordPunctTokenizer,
    TreebankWordTokenizer,
    TweetTokenizer,
    MWETokenizer,
    word_tokenize,
    sent_tokenize
)

# Stemmers
from nltk.stem import PorterStemmer, SnowballStemmer

# Lemmatizer
from nltk.stem import WordNetLemmatizer

# Download required datasets
nltk.download('punkt')
nltk.download('wordnet')

# Sample Text
text = "NLP is amazing! It helps computers understand language."

print("\nOriginal Text:")
print(text)

# ------------------------------------------------
# 1️⃣ Whitespace Tokenization
# ------------------------------------------------
print("\nWhitespace Tokenization:")

ws_tokenizer = WhitespaceTokenizer()
print(ws_tokenizer.tokenize(text))


# ------------------------------------------------
# 2️⃣ Punctuation-based Tokenization
# ------------------------------------------------
print("\nPunctuation-based Tokenization:")

punct_tokenizer = WordPunctTokenizer()
print(punct_tokenizer.tokenize(text))


# ------------------------------------------------
# 3️⃣ Treebank Tokenization
# ------------------------------------------------
print("\nTreebank Tokenization:")

treebank_tokenizer = TreebankWordTokenizer()
print(treebank_tokenizer.tokenize(text))


# ------------------------------------------------
# 4️⃣ Tweet Tokenization
# ------------------------------------------------
print("\nTweet Tokenization:")

tweet_tokenizer = TweetTokenizer()
print(tweet_tokenizer.tokenize(text))


# ------------------------------------------------
# 5️⃣ MWE (Multi-Word Expression) Tokenization
# ------------------------------------------------
print("\nMWE Tokenization:")

mwe_tokenizer = MWETokenizer([('New', 'York')])

mwe_text = "I live in New York city"
print(mwe_tokenizer.tokenize(mwe_text.split()))


# ------------------------------------------------
# 6️⃣ Porter Stemmer
# ------------------------------------------------
print("\nPorter Stemmer:")

ps = PorterStemmer()

words = word_tokenize(text)

porter_stems = [ps.stem(w) for w in words]

print(porter_stems)


# ------------------------------------------------
# 7️⃣ Snowball Stemmer
# ------------------------------------------------
print("\nSnowball Stemmer:")

ss = SnowballStemmer("english")

snowball_stems = [ss.stem(w) for w in words]

print(snowball_stems)


# ------------------------------------------------
# 8️⃣ Lemmatization
# ------------------------------------------------
print("\nLemmatization:")

lemmatizer = WordNetLemmatizer()

lemmas = [lemmatizer.lemmatize(w) for w in words]

print(lemmas)