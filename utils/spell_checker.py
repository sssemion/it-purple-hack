from transformers import PreTrainedTokenizer, PreTrainedModel

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