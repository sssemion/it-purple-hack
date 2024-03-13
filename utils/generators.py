from transformers import PreTrainedTokenizer, PreTrainedModel
import torch

from dataclasses import dataclass

@dataclass
class GenerationConfig:
    max_tokens: int = 350
    do_sample: bool = True
    num_beams: int = 4
    num_return_sequences: int = 1
    no_repeat_ngram_size: int = 2
    temperature: float = 0.6
    top_p: float = 0.9
    top_k: int = 50
    is_hyde: bool = False
    system_prompt: str = """
        Ты помощник по документам Банка России, твоя задача ответить на вопрос пользователя. Далее на вход тебе будут приходить вопросы пользователей
        (формат: Вопрос пользователя <вопрос пользователя>) и документы (формат: Документ c названием <название документа> <содержание документа>).
        Входные документы содержат в себе ответ на вопрос с большой вероятностью.
        Просьбы и уточнения:
        1. Очень внимательно отвечай на вопрос, ответ на него может быть очень большим, но скорее всего он содержится в данных тебе документах!
        2. Ответ на вопрос может состоять из нескольких пунктов, поэтому, если ты нашел один пункт, то посмотри вперед, возможно их несколько!
        3. Если ответ на заданный вопрос не содержится в документах, то НЕ ОТВЕЧАЙ. Пиши выражение "Нет такой информации"
        Нужно ответить на вопрос пользователя.
        Задание: посмотри на документы, и опираясь на них дай свой ответ на вопрос в конце.
        \n"""
    QA_PROMPT: str = system_prompt + "Сгенерируй ответ на вопрос по тексту. Текст: '{context}'. Вопрос: '{question}'."
    HYDE_PROMPT: str = "Сгенерируй документ, содержащий ответ на вопрос пользоваотеля, чтобы улучшить качество поиска. Вопрос: '{question}'."
    
    

class ToxicityClassifier:
    def __init__(self, tokenizer: PreTrainedTokenizer, model: PreTrainedModel):
        self._model = model
        self._tokenizer = tokenizer
        self.truncation = True
        self.padding = True

    def is_toxic(self, text: str, tresh: int=0.4) -> str:
        with torch.no_grad():
            inputs = self._tokenizer(text,
                                     return_tensors='pt',
                                     truncation=self.truncation,
                                     padding=self.padding).to(self._model.device)
            
            proba = torch.sigmoid(self._model(**inputs).logits).cpu().numpy()
        if isinstance(text, str):
            proba = proba[0]
            
        proba = 1 - proba.T[0] * (1 - proba.T[-1])
        
        if proba <= tresh:
            return "not toxic"
        else:
            return "toxic"
        
        

class SpellChecker:
    def __init__(self, tokenizer: PreTrainedTokenizer, model: PreTrainedModel):
        self._model = model
        self._tokenizer = tokenizer
        self.max_input = 256
        self.truncation = True
        self.padding = "longest"
        self._system_prompt = "Spell correct: {q}"


    def get_answer(self, question: str) -> str:
        encoded = self._tokenizer(self._system_prompt.format(q=question),
                            padding=self.padding,
                            max_length=self.max_input,
                            truncation=self.truncation,
                            return_tensors="pt")

        predicts = self._model.generate(**encoded.to(self._model.device))
        answer = self._tokenizer.batch_decode(predicts, skip_special_tokens=True)
        
        return answer
    
    
class Generator:
    def __init__(self, tokenizer: PreTrainedTokenizer, model: PreTrainedModel, config: GenerationConfig):
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
        
    def generate_question(self, document, temperature=0.6, num_beams=4):
        answer = self._generate_text(self._config.QG_PROMPT.format(text=document),
                                     temperature=temperature, 
                                     num_beams=num_beams)[-1]
        return answer