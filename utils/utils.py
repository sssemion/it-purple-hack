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
    
    
    

class Generator:
    def __init__(self, tokenizer, model, config):
        self._model = model
        self._tokenizer = tokenizer
        self._config = config
        self._max_tokens = self._config.max_tokens
        self._system_prompt = self._config.system_prompt

    def _generate_text(self, prompt, temperature, num_beams, n=1):
            encoded_input = self._tokenizer.encode_plus(prompt, return_tensors='pt')

            encoded_input = {k: v.to(self._model.device) for k, v in encoded_input.items()}

            resulted_tokens = self._model.generate(**encoded_input,
                                                  max_new_tokens=self._max_tokens,
                                                  do_sample=self._config.do_sample,
                                                  num_beams=num_beams,
                                                  num_return_sequences=self._config.num_return_sequences,
                                                  no_repeat_ngram_size=self._config.no_repeat_ngram_size,
                                                  temperature=temperature,
                                                  top_p=self._config.top_p,
                                                  top_k=self._config.top_k)

            resulted_texts = self._tokenizer.batch_decode(resulted_tokens, skip_special_tokens=True)

            return resulted_texts

    def get_answer(self, question, documents, urls, temperature=0.6, num_beams=4):
        documents_retriever = ''
        formatted_urls = 'Использованные документы:\n'
        for index, url in enumerate(urls):
            formatted_urls += f'{index+1}) {url} \n'
        for i in range(len(documents)):
            documents_retriever += f'Документ c номером {i}: {documents[i]} \n'
        
        answer = self._generate_text(self._config.QA_PROMPT.format(context=documents_retriever, question=question),
                                     temperature=temperature, 
                                     num_beams=num_beams)[-1]
        answer = answer + '\n\n' + formatted_urls
        return answer
    
    def hyde(self, question, temperature=0.6, num_beams=4):
        answer = self._generate_text(self._config.HYDE_PROMPT.format(question=question),
                                     temperature=temperature, 
                                     num_beams=num_beams)[-1]
        return answer
        
