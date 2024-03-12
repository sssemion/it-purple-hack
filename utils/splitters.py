from nltk.tokenize import sent_tokenize


class Chunker:
    def __init__(self, max_chunk_len=2500, overlap_len=50):
        self._max_chunk_len = max_chunk_len
        self._overlap_len = overlap_len
        self._tokenizer = sent_tokenize

    @staticmethod
    def _join_docs(docs, separator):
        text = separator.join(docs).strip()
        if text == "":
            return None
        else:
            return text

    def create_chunks(self, text, url, separator='\n'):
        sep_len = len(separator)
        tokenized_text = self._tokenizer(text, language='russian')
        chunks = []
        cur_chunk = []
        total_len = 0

        for sentence in tokenized_text:
            sentence_len = len(sentence)
            if total_len + sentence_len + (sep_len if len(cur_chunk) > 0 else 0) > self._max_chunk_len:
                if total_len > self._max_chunk_len:
                    pass
                if len(cur_chunk) > 0:
                    doc = self._join_docs(cur_chunk, separator)
                    if doc is not None:
                        chunks.append(doc)

                    while (total_len > self._overlap_len or
                           (total_len + sentence_len + (sep_len if len(cur_chunk) > 0 else 0) > self._max_chunk_len and
                            total_len > 0)):
                        total_len -= len(cur_chunk[0]) + (sep_len if len(cur_chunk) > 1 else 0)
                        cur_chunk = cur_chunk[1:]
            cur_chunk.append(sentence)
            total_len += sentence_len + (sep_len if len(cur_chunk) > 1 else 0)

        doc = self._join_docs(cur_chunk, separator)

        if doc is not None:
            chunks.append(doc)
        urls = [url] * len(chunks)
        return chunks, urls

    def split_texts(self, texts):
        chunks = []
        urls = []
        for ind, text in texts.iterrows():
            cur_chunks, cur_urls = self.create_chunks(text.text, text.name)
            chunks.extend(cur_chunks)
            urls.extend(cur_urls)
        return chunks, urls
