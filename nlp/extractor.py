import spacy

# load spaCy model once (French + English since finance is mixed)
try:
    nlp = spacy.load("fr_core_news_md")
except OSError:
    # fallback to English if French not installed
    nlp = spacy.load("en_core_web_md")


# Later replace 
def extract_core_sentences(text: str, max_sentences: int = 3):
    """
    Extract the most 'informative' sentences from raw text.
    For now: simple heuristic = sentence length + presence of numbers/named entities.
    Later: replace with LLM summarization.
    """
    doc = nlp(text)
    sentences = []

    for sent in doc.sents:
        score = 0
        # heuristic 1: sentence with numbers = likely financial info
        if any(tok.like_num for tok in sent):
            score += 2
        # heuristic 2: contains named entities (orgs, persons, etc.)
        if any(ent.label_ in {"ORG", "PERSON", "MONEY", "DATE"} for ent in sent.ents):
            score += 2
        # heuristic 3: length not too short
        if len(sent) > 40:
            score += 1

        sentences.append((score, sent.text.strip()))

    # sort by score and keep top n
    sentences = sorted(sentences, key=lambda x: x[0], reverse=True)
    return [s for _, s in sentences[:max_sentences]]
